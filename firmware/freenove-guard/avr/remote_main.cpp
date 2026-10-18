#include <Arduino.h>

#include "FNHRRemote.h"
#include "freenove_guard/frame.h"
#include "freenove_guard/rf_link.h"

void serialEvent() {}

namespace {

using namespace freenove_guard;

FNHRRemote remote;
uint8_t radio_packet[32];
uint8_t stop_match = 0U;
uint32_t stop_started_ms = 0U;

enum class ManualPhase : uint8_t { Idle, Holding, StatusPending, BeginPending, ArmPending, Armed };
ManualPhase manual_phase = ManualPhase::Idle;
uint32_t manual_hold_started_ms = 0U;
bool stop_sent = false;
uint32_t manual_phase_deadline_ms = 0U;
uint32_t manual_keepalive_due_ms = 0U;
uint32_t manual_sequence = 0U;
uint32_t manual_begin_sequence = 0U;
uint8_t manual_attempt = 0U;
bool keepalive_pending = false;
uint32_t keepalive_deadline_ms = 0U;
uint8_t manual_identifier[8] = {};

bool send_radio(uint8_t source, const Frame& frame) {
  uint8_t packet[32] = {};
  uint8_t size = 0U;
  return wrap_rf(source, frame, packet, size) && remote.SendPacket(packet, size);
}

void make_identifier(uint32_t sequence) {
  manual_identifier[0] = 'm';
  manual_identifier[1] = 'a';
  manual_identifier[2] = 'n';
  manual_identifier[3] = 'u';
  manual_identifier[4] = static_cast<uint8_t>(sequence & 0xffU);
  manual_identifier[5] = static_cast<uint8_t>((sequence >> 8U) & 0xffU);
  manual_identifier[6] = static_cast<uint8_t>((sequence >> 16U) & 0xffU);
  manual_identifier[7] = ++manual_attempt;
}

bool send_command(uint8_t source, uint8_t opcode, uint32_t sequence) {
  Command command{opcode, sequence, 0U, {manual_identifier[0], manual_identifier[1], manual_identifier[2],
                                          manual_identifier[3], manual_identifier[4], manual_identifier[5],
                                          manual_identifier[6], manual_identifier[7]}};
  Frame frame{};
  return encode_command(command, frame) && send_radio(source, frame);
}

void send_stop_burst() {
  uint8_t packet[32] = {};
  uint8_t size = 0U;
  if (!make_rf_stop(kRfStopSource, packet, size)) return;
  for (uint8_t count = 0U; count < 3U; ++count) remote.SendPacket(packet, size);
}

class ForwardValidator final : public FrameObserver {
 public:
  void on_command(const Command& command) override {
    Frame frame{};
    if (encode_command(command, frame)) send_radio(kRfComputerSource, frame);
  }

  void on_stop() override { send_stop_burst(); }
  void on_frame_error(Result) override {}

  void receive(uint8_t value, uint32_t now_ms) {
    if (stop_match != 0U && static_cast<uint32_t>(now_ms - stop_started_ms) >= 50U) stop_match = 0U;
    if (stop_match == 0U && value == kStart) {
      stop_match = 1U;
      stop_started_ms = now_ms;
    } else if (stop_match == 1U && value == kStop) {
      stop_match = 2U;
    } else if (stop_match == 2U && value == kEnd) {
      stop_match = 0U;
      decoder_.reset();
      send_stop_burst();
      return;
    } else if (value == kStart) {
      stop_match = 1U;
      stop_started_ms = now_ms;
    } else {
      stop_match = 0U;
    }
    decoder_.feed(value, now_ms, *this);
  }

  void tick(uint32_t now_ms) { decoder_.tick(now_ms, *this); }

 private:
  FrameDecoder decoder_;
};

ForwardValidator host;

void disarm_manual() {
  remote.SetManualEnabled(false);
  manual_phase = ManualPhase::Idle;
  keepalive_pending = false;
}

void accept_manual_reply(const Frame& frame, uint32_t now_ms) {
  Reply reply{};
  if (!decode_reply(frame, reply)) return;
  if (reply.state == State::Fault) {
    disarm_manual();
    return;
  }
  if (manual_phase == ManualPhase::StatusPending && reply.opcode == 0x33U &&
      reply.result == Result::Accepted && (reply.state == State::Boot || reply.state == State::Disarmed)) {
    if (reply.state == State::Boot) manual_begin_sequence = 0U;
    else if (reply.sequence < kMaxSequence) manual_begin_sequence = reply.sequence + 1U;
    else { disarm_manual(); return; }
    make_identifier(manual_begin_sequence);
    if (send_command(kRfManualSource, kBegin, manual_begin_sequence)) {
      manual_phase = ManualPhase::BeginPending;
      manual_phase_deadline_ms = now_ms + 500U;
    } else disarm_manual();
  } else if (manual_phase == ManualPhase::BeginPending && reply.opcode == 0x29U &&
             reply.sequence == manual_begin_sequence && reply.result == Result::Accepted &&
             reply.state == State::Session && manual_begin_sequence < kMaxSequence &&
             send_command(kRfManualSource, kArm, manual_begin_sequence + 1U)) {
    manual_sequence = manual_begin_sequence;
    manual_phase = ManualPhase::ArmPending;
    manual_phase_deadline_ms = now_ms + 500U;
  } else if (manual_phase == ManualPhase::ArmPending && reply.opcode == 0x2bU &&
             reply.sequence == manual_begin_sequence + 1U && reply.result == Result::Accepted &&
             reply.state == State::Armed) {
    manual_sequence = reply.sequence;
    manual_phase = ManualPhase::Armed;
    remote.SetManualEnabled(true);
    manual_keepalive_due_ms = now_ms + 100U;
  } else if (manual_phase == ManualPhase::Armed && keepalive_pending && reply.opcode == 0x2dU &&
             reply.sequence == manual_sequence + 1U && reply.result == Result::Accepted) {
    manual_sequence = reply.sequence;
    keepalive_pending = false;
    manual_keepalive_due_ms = now_ms + 100U;
  } else if (manual_phase != ManualPhase::Armed && reply.result != Result::Accepted) {
    disarm_manual();
  }
}

void receive_radio(uint32_t now_ms) {
  uint8_t size = 0U;
  uint8_t pipe = 0U;
  while (remote.ReceivePacket(radio_packet, size, pipe)) {
    uint8_t source = 0U;
    Frame frame{};
    if (!unwrap_rf(radio_packet, size, source, frame) || source != kRfRobotSource) continue;
    if (pipe == 2U) accept_manual_reply(frame, now_ms);
    else if (pipe == 1U && Serial.availableForWrite() >= frame.size) Serial.write(frame.bytes, frame.size);
  }
}

void update_manual(uint32_t now_ms) {
  const bool switches_off = digitalRead(4) == HIGH && digitalRead(3) == HIGH && digitalRead(2) == HIGH;
  const bool stop_pressed = digitalRead(4) == LOW && digitalRead(3) == LOW && digitalRead(2) == LOW;
  if (stop_pressed) {
    disarm_manual();
    if (!stop_sent) send_stop_burst();
    stop_sent = true;
    manual_phase = ManualPhase::Idle;
    return;
  }
  stop_sent = false;
  if ((manual_phase == ManualPhase::StatusPending || manual_phase == ManualPhase::BeginPending ||
       manual_phase == ManualPhase::ArmPending) &&
      static_cast<uint32_t>(now_ms - manual_phase_deadline_ms) < 0x80000000UL) {
    send_stop_burst();
    disarm_manual();
    return;
  }
  if (manual_phase == ManualPhase::Armed && keepalive_pending &&
      static_cast<uint32_t>(now_ms - keepalive_deadline_ms) < 0x80000000UL) {
    send_stop_burst();
    disarm_manual();
    return;
  }
  const bool button_pressed = digitalRead(7) == LOW;
  if (manual_phase == ManualPhase::Holding && !switches_off) {
    disarm_manual();
    return;
  }
  if (manual_phase == ManualPhase::Idle && button_pressed && switches_off) {
    manual_phase = ManualPhase::Holding;
    manual_hold_started_ms = now_ms;
  } else if (manual_phase == ManualPhase::Holding && !button_pressed) {
    if (switches_off && static_cast<uint32_t>(now_ms - manual_hold_started_ms) >= 1000U &&
        send_command(kRfManualSource, kStatus, 0U)) {
      manual_phase = ManualPhase::StatusPending;
      manual_phase_deadline_ms = now_ms + 500U;
    } else disarm_manual();
  }
  if (manual_phase == ManualPhase::Armed) {
    if (!keepalive_pending && static_cast<uint32_t>(now_ms - manual_keepalive_due_ms) < 0x80000000UL) {
      if (manual_sequence >= kMaxSequence || !send_command(kRfManualSource, kKeepalive, manual_sequence + 1U)) {
        send_stop_burst();
        disarm_manual();
        return;
      }
      keepalive_pending = true;
      keepalive_deadline_ms = now_ms + 500U;
    }
    remote.Update();
  }
}

}

void setup() {
  Serial.begin(115200);
  remote.Start();
  remote.SetManualEnabled(false);
}

void loop() {
  const uint32_t now_ms = millis();
  for (uint8_t count = 0U; count < 32U && Serial.available() > 0; ++count) {
    host.receive(static_cast<uint8_t>(Serial.read()), now_ms);
  }
  host.tick(now_ms);
  receive_radio(now_ms);
  update_manual(now_ms);
}
