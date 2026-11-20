#include <Arduino.h>
#include <avr/interrupt.h>

#include "guard_state.h"
#include "freenove_guard/esp_diag.h"
#include "freenove_guard/expressive_motion.h"
#include "freenove_guard/joint_bench.h"
#include "freenove_guard/scheduler.h"

namespace {

uint8_t serial_count = 0U;
uint8_t serial_order = 0U;
class Serial2Port final : public freenove_guard::EspPort {
 public:
  uint8_t available() const override { return static_cast<uint8_t>(Serial2.available()); }
  uint8_t read() override { return static_cast<uint8_t>(Serial2.read()); }
  bool writable(uint8_t size) const override { return Serial2.availableForWrite() >= size; }
  void write(const uint8_t* bytes, uint8_t size) override { Serial2.write(bytes, size); }
};

Serial2Port serial2_port;
freenove_guard::EspDiagnostics esp_diagnostics(serial2_port);

void emit_diagnostic(HardwareSerial& port, uint8_t order) {
  if (order == 0U) {
    const uint8_t response[] = {0x80U, 0x01U, 0x81U};
    if (port.availableForWrite() >= sizeof(response)) port.write(response, sizeof(response));
    return;
  }
  const int supply = static_cast<int>(robot_action.robot.power.voltage * 100.0F);
  const uint8_t response[] = {0x80U, 0x0bU, static_cast<uint8_t>(supply / 128),
                              static_cast<uint8_t>(supply % 128), 0x81U};
  if (port.availableForWrite() >= sizeof(response)) port.write(response, sizeof(response));
}

bool compatibility_byte(uint8_t value, uint8_t& count, uint8_t& order) {
  if (count == 0U && value == 0x80U) {
    count = 1U;
    return true;
  }
  if (count == 1U && (value == 0U || value == 0x0aU)) {
    order = value;
    count = 2U;
    return true;
  }
  if (count == 2U && value == 0x81U) {
    count = 0U;
    return true;
  }
  count = value == 0x80U ? 1U : 0U;
  return false;
}

Point vendor_point(const freenove_guard::FootPoint& foot) {
  return Point(foot.x, foot.y, foot.z);
}

RobotLegsPoints vendor_stance(const freenove_guard::Stance& stance) {
  return RobotLegsPoints(vendor_point(stance.feet[0]), vendor_point(stance.feet[1]),
                         vendor_point(stance.feet[2]), vendor_point(stance.feet[3]),
                         vendor_point(stance.feet[4]), vendor_point(stance.feet[5]));
}

freenove_guard::FootPoint foot_point(const Point& point) {
  return {point.x, point.y, point.z};
}

class ExpressiveRobot final : public freenove_guard::ExpressiveSink {
 public:
  explicit ExpressiveRobot(Robot& robot)
      : robot_(robot), legs_{&robot.leg1, &robot.leg2, &robot.leg3, &robot.leg4,
                            &robot.leg5, &robot.leg6} {}

  bool reachable(uint8_t leg_index, const freenove_guard::FootPoint& foot) override {
    return !terminal_fault && legs_[leg_index]->CheckPoint(vendor_point(foot));
  }

  bool move(const freenove_guard::Stance& stance, float step_mm) override {
    if (terminal_fault) return false;
    robot_.MoveTo(vendor_stance(stance), step_mm);
    robot_.WaitUntilFree();
    return !terminal_fault;
  }

  bool hold(uint16_t milliseconds) override {
    if (terminal_fault) return false;
    delay(milliseconds);
    return !terminal_fault;
  }

 private:
  Robot& robot_;
  RobotLeg* const legs_[6];
};

bool run_expressive_action(freenove_guard::Action action) {
  Robot& robot = robot_action.robot;
  if (robot.state != Robot::Action) return false;
  RobotLegsPoints points;
  robot.GetPointsNow(points);
  const freenove_guard::Stance initial{{foot_point(points.leg1), foot_point(points.leg2),
      foot_point(points.leg3), foot_point(points.leg4), foot_point(points.leg5),
      foot_point(points.leg6)}};
  ExpressiveRobot sink(robot);
  return freenove_guard::run_expressive(action, initial, sink);
}

#ifdef FURBOMEK_JOINT_BENCH
bool run_joint_probe(const freenove_guard::JointProbe& probe) {
  Robot& robot = robot_action.robot;
  if (terminal_fault || robot.state != Robot::Action) return false;
  RobotLeg* legs[] = {&robot.leg1, &robot.leg2, &robot.leg3,
                      &robot.leg4, &robot.leg5, &robot.leg6};
  for (const RobotLeg* leg : legs) {
    const float z = leg->pointNow.z;
    if (!(z >= -18.0F && z <= -12.0F)) return false;
  }
  RobotLeg& leg = *legs[probe.leg];
  const Point initial = leg.pointNow;
  float start[3] = {};
  leg.CalculateAngle(initial, start[0], start[1], start[2]);
  Point points[3];
  for (uint8_t index = 0U; index < 3U; ++index) {
    float angles[3] = {start[0], start[1], start[2]};
    angles[probe.axis] += static_cast<float>(probe.offset_deg) *
                          static_cast<float>(index + 1U) / 3.0F;
    if (terminal_fault || !leg.CheckAngle(angles[0], angles[1], angles[2])) return false;
    leg.CalculatePoint(angles[0], angles[1], angles[2], points[index]);
    if (!leg.CheckPoint(points[index]) ||
        !(Point::GetDistance(initial, points[index]) <= 45.0F)) return false;
  }
  robot.SetSpeed(probe.step_mm);
  for (const Point& point : points) {
    if (terminal_fault) return false;
    leg.MoveTo(point);
    leg.WaitUntilFree();
    if (terminal_fault) return false;
    delay(130U);
  }
  for (int8_t index = 1; index >= 0; --index) {
    if (terminal_fault) return false;
    leg.MoveTo(points[index]);
    leg.WaitUntilFree();
  }
  if (terminal_fault) return false;
  leg.MoveTo(initial);
  leg.WaitUntilFree();
  return !terminal_fault;
}

bool run_bench_height(float height) {
  Robot& robot = robot_action.robot;
  if (terminal_fault || robot.state != Robot::Action) return false;
  RobotLegsPoints start;
  robot.GetPointsNow(start);
  const float initial_z = start.leg1.z;
  if (!(initial_z >= -25.0F && initial_z <= -7.0F)) return false;
  const Point* current[] = {&start.leg1, &start.leg2, &start.leg3,
                            &start.leg4, &start.leg5, &start.leg6};
  for (const Point* foot : current) {
    if (!(foot->z >= initial_z - 0.5F && foot->z <= initial_z + 0.5F)) return false;
  }
  RobotLegsPoints targets[3];
  for (uint8_t index = 0U; index < 3U; ++index) {
    targets[index] = start;
    auto& target = targets[index];
    const float z = initial_z + (height - initial_z) * (index + 1U) / 3.0F;
    target.leg1.z = target.leg2.z = target.leg3.z = z;
    target.leg4.z = target.leg5.z = target.leg6.z = z;
    if (terminal_fault || !robot.CheckPoints(target)) return false;
  }
  for (const auto& target : targets) {
    if (terminal_fault) return false;
    robot.MoveTo(target, 3.0F);
    robot.WaitUntilFree();
  }
  if (terminal_fault) return false;
  delay(400U);
  return !terminal_fault;
}
#endif

void receive_serial(uint8_t value, freenove_guard::ClockSample clock) {
  const uint8_t previous_count = serial_count;
  const uint8_t previous_order = serial_order;
  if (compatibility_byte(value, serial_count, serial_order)) {
    if (previous_count == 2U && value == 0x81U) emit_diagnostic(Serial, previous_order);
    return;
  }
  if (previous_count != 0U) {
    dispatcher.receive_usb(0x80U, clock.now_ms);
    if (previous_count == 2U) dispatcher.receive_usb(previous_order, clock.now_ms);
  }
  dispatcher.receive_usb(value, clock.now_ms);
}

void sync_deadlines(freenove_guard::ClockSample clock) {
  const freenove_guard::Snapshot snapshot = dispatcher.snapshot(clock.now_ms);
  const uint8_t saved_status = SREG;
  cli();
  if (terminal_fault || !snapshot.deadlines_active) {
    timer_deadlines_active = false;
    transport_deadline_tick = 0U;
    session_deadline_tick = 0U;
    SREG = saved_status;
    return;
  }
  if (snapshot.deadlines_active && !timer_deadlines_active) {
    session_deadline_tick = clock.ticks + 3000UL;
    timer_deadlines_active = true;
  }
  if (snapshot.deadlines_active && snapshot.transport_remaining_ms > 0U) {
    transport_deadline_tick = freenove_guard::mirror_transport_deadline(
        transport_deadline_tick, clock, snapshot.transport_remaining_ms);
  }
  SREG = saved_status;
}

void run_vendor(const uint8_t* action, uint8_t size) {
  switch (action[1]) {
    case 96U: robot_action.SwitchMode(); break;
    case 110U: robot_action.Crawl(action[2] - 64, action[3] - 64, action[4] - 64); break;
    case 112U: robot_action.ChangeBodyHeight(action[2] - 64); break;
    case 114U: robot_action.MoveBody(action[2] - 64, action[3] - 64, action[4] - 64); break;
    case 118U:
      if (size == 9U) robot_action.TwistBody(Point(action[2] - 64, action[3] - 64, action[4] - 64),
                                              Point(action[5] - 64, action[6] - 64, action[7] - 64));
      break;
    default: break;
  }
}

}

void guard_service() {
  const freenove_guard::ClockSample entry_clock = clock_sample();
  if (terminal_fault) dispatcher.external_fault(entry_clock.now_ms);
  if (operation_done_pending) {
    operation_done_pending = false;
    operation_active = false;
    if (!terminal_fault) dispatcher.operation_done();
  }
  for (uint8_t count = 0U; count < 32U && Serial.available() > 0; ++count) {
    const uint8_t value = static_cast<uint8_t>(Serial.read());
    const freenove_guard::ClockSample event_clock = clock_sample();
    receive_serial(value, event_clock);
    sync_deadlines(event_clock);
  }
  const uint16_t supply = static_cast<uint16_t>(robot_action.robot.power.voltage * 100.0F);
  esp_diagnostics.tick(entry_clock.now_ms, supply);
  for (uint8_t count = 0U; count < 3U && robot_radio.available(); ++count) {
    const uint8_t size = robot_radio.getDynamicPayloadSize();
    if (size == 0U || size > sizeof(rf_packet)) {
      robot_radio.flush_rx();
      continue;
    }
    robot_radio.read(rf_packet, size);
    const freenove_guard::ClockSample event_clock = clock_sample();
    dispatcher.receive_radio(rf_packet, size, event_clock.now_ms);
    sync_deadlines(event_clock);
  }
  const freenove_guard::ClockSample final_clock = clock_sample();
  dispatcher.tick(final_clock.now_ms);
  sync_deadlines(final_clock);
}

void guard_action() {
  uint8_t vendor[9] = {};
  uint8_t vendor_size = 0U;
  const uint8_t saved_status = SREG;
  cli();
  const freenove_guard::PendingOperation pending = freenove_guard::admitted_operation(
      terminal_fault, action_pending, pending_vendor_size != 0U,
      static_cast<freenove_guard::Action>(pending_action));
  if (pending.kind == freenove_guard::PendingKind::Vendor) {
    vendor_size = pending_vendor_size;
    for (uint8_t index = 0U; index < vendor_size; ++index) vendor[index] = pending_vendor[index];
    pending_vendor_size = 0U;
  } else if (pending.kind == freenove_guard::PendingKind::Guarded) {
    action_pending = false;
  }
  SREG = saved_status;
  if (pending.kind == freenove_guard::PendingKind::None) return;
  if (vendor_size != 0U) run_vendor(vendor, vendor_size);
  else {
#ifdef FURBOMEK_JOINT_BENCH
    freenove_guard::JointProbe probe{};
    float height = 0.0F;
    const auto code = static_cast<uint8_t>(pending.action);
    if (freenove_guard::bench_action_code(code)) {
      const bool completed = freenove_guard::decode_joint_probe(code, probe)
          ? run_joint_probe(probe)
          : freenove_guard::decode_bench_height(code, height) && run_bench_height(height);
      if (!completed) safe_outputs();
      if (!terminal_fault) operation_done_pending = true;
      return;
    }
#endif
    switch (pending.action) {
      case freenove_guard::Action::Active: robot_action.ActiveMode(); break;
      case freenove_guard::Action::Sleep: robot_action.SleepMode(); break;
      case freenove_guard::Action::CrawlForward: robot_action.CrawlForward(); break;
      case freenove_guard::Action::CrawlBackward: robot_action.CrawlBackward(); break;
      case freenove_guard::Action::CrawlLeft: robot_action.CrawlLeft(); break;
      case freenove_guard::Action::CrawlRight: robot_action.CrawlRight(); break;
      case freenove_guard::Action::TurnLeft: robot_action.TurnLeft(); break;
      case freenove_guard::Action::TurnRight: robot_action.TurnRight(); break;
      case freenove_guard::Action::Poke:
      case freenove_guard::Action::DefensiveBrace:
      case freenove_guard::Action::TuckPreview:
        if (!run_expressive_action(pending.action)) safe_outputs();
        break;
    }
  }
  if (!terminal_fault) operation_done_pending = true;
}
