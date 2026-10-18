#include <EEPROM.h>
#include <FlexiTimer2.h>
#include <SPI.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>

#include "guard_runtime.h"
#include "guard_state.h"
#include "freenove_guard/metadata.h"

bool deadline_margin_locked();
void quiesce_outputs_locked(bool latch_fault);

namespace {

constexpr uint8_t kEnableMask = _BV(PK6) | _BV(PK7);
constexpr uint8_t kServoD38Mask = _BV(PD7);
constexpr uint8_t kServoD39Mask = _BV(PG2);
uint8_t saved_pwm_interrupts = 0U;

class Motion final : public freenove_guard::MotionSink {
 public:
  bool metadata_supported() const override {
    return !terminal_fault && freenove_guard::metadata_supported(EEPROM.read(0), EEPROM.read(3));
  }

  uint16_t supply_centivolts() const override {
    const float centivolts = robot_action.robot.power.voltage * 100.0F;
    if (!(centivolts > 0.0F)) return 0U;
    if (centivolts >= 16383.0F) return 16383U;
    return static_cast<uint16_t>(centivolts);
  }

  bool arm_start() override {
    const uint8_t saved_status = SREG;
    cli();
    const bool accepted = deadline_safe_locked();
    if (accepted) {
      PORTK &= static_cast<uint8_t>(~kEnableMask);
      if ((saved_pwm_interrupts & 0x01U) != 0U) TIMSK1 |= _BV(OCIE1A);
      if ((saved_pwm_interrupts & 0x02U) != 0U) TIMSK3 |= _BV(OCIE3A);
      if ((saved_pwm_interrupts & 0x04U) != 0U) TIMSK5 |= _BV(OCIE5A);
      arm_stage = 1U;
      arm_stage_deadline_tick = timer4_ticks + 4U;
    }
    SREG = saved_status;
    return accepted;
  }

  bool arm_ready() override { return !terminal_fault && arm_stage == 3U && deadline_safe_locked(); }

  bool normal_disarm() override {
    const uint8_t saved_status = SREG;
    cli();
    const bool accepted = deadline_margin_locked();
    if (accepted) {
      quiesce_outputs_locked(false);
      timer_deadlines_active = false;
      transport_deadline_tick = 0U;
      session_deadline_tick = 0U;
    }
    SREG = saved_status;
    return accepted;
  }

  bool execute(freenove_guard::Action action) override {
    const uint8_t saved_status = SREG;
    cli();
    const bool accepted = deadline_safe_locked() && !action_pending && pending_vendor_size == 0U;
    if (accepted) {
      pending_action = static_cast<uint8_t>(action);
      action_pending = true;
      operation_active = true;
      operation_deadline_tick = timer4_ticks + 300U;
    }
    SREG = saved_status;
    return accepted;
  }

  bool execute_vendor(const freenove_guard::VendorAction& action) override {
    const uint8_t saved_status = SREG;
    cli();
    const bool accepted = deadline_safe_locked() && !action_pending && pending_vendor_size == 0U;
    if (accepted) {
      pending_vendor_size = action.size;
      for (uint8_t index = 0U; index < action.size; ++index) pending_vendor[index] = action.bytes[index];
      operation_active = true;
      operation_deadline_tick = timer4_ticks + 300U;
    }
    SREG = saved_status;
    return accepted;
  }

  void safe_stop() override { safe_outputs(); }
};

class Replies final : public freenove_guard::RoutedReplySink {
 public:
  void send(freenove_guard::ReplyRoute route, const freenove_guard::Frame& frame) override {
    if (route == freenove_guard::ReplyRoute::Usb) {
      if (Serial.availableForWrite() >= frame.size) Serial.write(frame.bytes, frame.size);
      return;
    }
    uint8_t packet[32] = {};
    uint8_t size = 0U;
    if (!freenove_guard::wrap_rf(freenove_guard::kRfRobotSource, frame, packet, size)) return;
    const uint8_t computer_address[6] = {'C', 'N', 'K', '2', 'R', 0};
    const uint8_t manual_address[6] = {'M', 'N', 'K', '2', 'R', 0};
    robot_radio.stopListening();
    robot_radio.openWritingPipe(route == freenove_guard::ReplyRoute::RadioManual ? manual_address : computer_address);
    robot_radio.write(packet, size);
    robot_radio.startListening();
  }
};

Motion motion;
Replies replies;

void setup_timer4() {
  TCCR4A = 0;
  TCCR4B = 0;
  TCNT4 = 0;
  OCR4A = 2499;
  TIFR4 = _BV(OCF4A);
  TIMSK4 = _BV(OCIE4A);
  TCCR4B = _BV(WGM42) | _BV(CS41) | _BV(CS40);
}

void vendor_update() {
  if (guard_service_active) return;
  guard_service_active = true;
  sei();
  guard_service();
  if (!terminal_fault && motion_updates) robot_action.robot.Update();
  else robot_action.robot.power.Update();
  guard_service();
  cli();
  guard_service_active = false;
}

}

RobotAction robot_action;
RF24 robot_radio(9, 53);
freenove_guard::Dispatcher dispatcher(motion, replies);
uint8_t rf_packet[32];
volatile bool terminal_fault = false;
volatile bool motion_updates = false;
volatile uint8_t arm_stage = 0U;
volatile uint32_t arm_stage_deadline_tick = 0U;
volatile bool action_pending = false;
volatile uint8_t pending_action = 0U;
volatile uint8_t pending_vendor[9] = {};
volatile uint8_t pending_vendor_size = 0U;
volatile bool operation_done_pending = false;
volatile bool operation_active = false;
volatile uint32_t operation_deadline_tick = 0U;
volatile uint32_t timer4_ticks = 0U;
volatile uint32_t transport_deadline_tick = 0U;
volatile uint32_t session_deadline_tick = 0U;
volatile bool timer_deadlines_active = false;
volatile bool guard_service_active = false;

freenove_guard::ClockSample clock_sample() {
  const uint8_t saved_status = SREG;
  cli();
  const uint32_t ticks = timer4_ticks;
  SREG = saved_status;
  return {ticks, ticks * 10UL};
}

bool deadline_reached(uint32_t now, uint32_t deadline) { return static_cast<int32_t>(now - deadline) >= 0; }

bool deadline_safe_locked() {
  return !terminal_fault && timer_deadlines_active &&
         !deadline_reached(timer4_ticks, transport_deadline_tick) &&
         !deadline_reached(timer4_ticks, session_deadline_tick);
}

bool deadline_margin_locked() {
  if (!deadline_safe_locked() || (TIFR4 & _BV(OCF4A)) != 0U) return false;
  return static_cast<int32_t>(transport_deadline_tick - timer4_ticks) >= 3 &&
         static_cast<int32_t>(session_deadline_tick - timer4_ticks) >= 3;
}

void quiesce_outputs_locked(bool latch_fault) {
  PORTK &= static_cast<uint8_t>(~kEnableMask);
  motion_updates = false;
  arm_stage = 0U;
  operation_active = false;
  action_pending = false;
  operation_done_pending = false;
  pending_vendor_size = 0U;
  TIMSK1 &= static_cast<uint8_t>(~_BV(OCIE1A));
  TIMSK3 &= static_cast<uint8_t>(~_BV(OCIE3A));
  TIMSK5 &= static_cast<uint8_t>(~_BV(OCIE5A));
  PORTA = 0;
  PORTC = 0;
  PORTD &= static_cast<uint8_t>(~kServoD38Mask);
  PORTG &= static_cast<uint8_t>(~kServoD39Mask);
  if (latch_fault) terminal_fault = true;
}

void safe_outputs() {
  const uint8_t saved_status = SREG;
  cli();
  quiesce_outputs_locked(true);
  timer_deadlines_active = false;
  transport_deadline_tick = 0U;
  session_deadline_tick = 0U;
  SREG = saved_status;
}

void guard_runtime_setup() {
  if (motion.metadata_supported()) robot_action.Start();
  saved_pwm_interrupts = static_cast<uint8_t>(((TIMSK1 & _BV(OCIE1A)) != 0U ? 0x01U : 0U) |
                                              ((TIMSK3 & _BV(OCIE3A)) != 0U ? 0x02U : 0U) |
                                              ((TIMSK5 & _BV(OCIE5A)) != 0U ? 0x04U : 0U));
  const uint8_t saved_status = SREG;
  cli();
  quiesce_outputs_locked(false);
  SREG = saved_status;
  Serial.begin(115200);
  Serial2.begin(115200);
  robot_radio.begin();
  robot_radio.setRetries(3, 15);
  robot_radio.setPALevel(RF24_PA_LOW, false);
  robot_radio.setDataRate(RF24_1MBPS);
  robot_radio.enableDynamicPayloads();
  robot_radio.setAutoAck(true);
  robot_radio.setChannel(125);
  const uint8_t address[6] = {'F', 'N', 'K', '2', '9', 0};
  robot_radio.openWritingPipe(address);
  robot_radio.openReadingPipe(1, address);
  robot_radio.startListening();
  FlexiTimer2::set(20, vendor_update);
  FlexiTimer2::start();
  setup_timer4();
  wdt_enable(WDTO_250MS);
}

void guard_runtime_loop() { guard_action(); }

void guard_runtime_timer4() {
  wdt_reset();
  ++timer4_ticks;
  if ((timer_deadlines_active && (deadline_reached(timer4_ticks, transport_deadline_tick) ||
       deadline_reached(timer4_ticks, session_deadline_tick))) ||
      (operation_active && deadline_reached(timer4_ticks, operation_deadline_tick))) {
    safe_outputs();
    return;
  }
  if (arm_stage == 1U && deadline_reached(timer4_ticks, arm_stage_deadline_tick) && deadline_safe_locked()) {
    PORTK |= _BV(PK7);
    arm_stage = 2U;
    arm_stage_deadline_tick = timer4_ticks + 2U;
  } else if (arm_stage == 2U && deadline_reached(timer4_ticks, arm_stage_deadline_tick) && deadline_safe_locked()) {
    PORTK |= _BV(PK6);
    arm_stage = 3U;
    motion_updates = true;
  }
}
