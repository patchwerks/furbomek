#include <Arduino.h>
#include <avr/interrupt.h>

#include "guard_state.h"
#include "freenove_guard/esp_diag.h"
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
    switch (pending.action) {
      case freenove_guard::Action::Active: robot_action.ActiveMode(); break;
      case freenove_guard::Action::Sleep: robot_action.SleepMode(); break;
      case freenove_guard::Action::CrawlForward: robot_action.CrawlForward(); break;
      case freenove_guard::Action::CrawlBackward: robot_action.CrawlBackward(); break;
      case freenove_guard::Action::CrawlLeft: robot_action.CrawlLeft(); break;
      case freenove_guard::Action::CrawlRight: robot_action.CrawlRight(); break;
      case freenove_guard::Action::TurnLeft: robot_action.TurnLeft(); break;
      case freenove_guard::Action::TurnRight: robot_action.TurnRight(); break;
    }
  }
  if (!terminal_fault) operation_done_pending = true;
}
