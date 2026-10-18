#include "freenove_guard/guard.h"

#include <string.h>

namespace freenove_guard {

namespace {

uint8_t reply_opcode(uint8_t opcode) { return static_cast<uint8_t>(opcode + 1U); }

}

Guard::Guard(MotionSink& motion, ReplySink& replies)
    : motion_(motion),
      replies_(replies),
      decoder_(),
      state_(State::Boot),
      now_ms_(0U),
      session_started_ms_(0U),
      transport_deadline_ms_(0U),
      operation_deadline_ms_(0U),
      sequence_(0U),
      fault_(0U),
      last_accepted_opcode_(0xffU),
      busy_(false),
      identifier_{},
      raw_stop_match_(0U),
      raw_stop_started_ms_(0U) {}

bool Guard::active() const {
  return state_ == State::Session || state_ == State::Arming || state_ == State::Armed;
}

bool Guard::sequence_ok(uint32_t sequence) const {
  return sequence_ < kMaxSequence && sequence == sequence_ + 1U;
}

bool Guard::begin_sequence_ok(const Command& command) const {
  if (state_ == State::Boot) return command.sequence == 0U;
  return state_ == State::Disarmed && sequence_ok(command.sequence) &&
         memcmp(identifier_, command.identifier, sizeof(identifier_)) != 0;
}

bool Guard::readonly_status() const {
  return state_ == State::Boot || state_ == State::Fault || state_ == State::Disarmed;
}

uint16_t Guard::remaining(uint32_t now_ms, uint32_t deadline) const {
  const uint32_t left = deadline - now_ms;
  return left > 0x3fffU ? 0x3fffU : static_cast<uint16_t>(left);
}

void Guard::receive(uint8_t value, uint32_t now_ms) {
  now_ms_ = now_ms;
  if (raw_stop_match_ != 0U && static_cast<uint32_t>(now_ms - raw_stop_started_ms_) >= 50U) {
    raw_stop_match_ = 0U;
  }
  if (raw_stop_match_ == 0U && value == kStart) {
    raw_stop_match_ = 1U;
    raw_stop_started_ms_ = now_ms;
  } else if (raw_stop_match_ == 1U && value == kStop) {
    raw_stop_match_ = 2U;
    return;
  } else if (raw_stop_match_ == 2U && value == kEnd) {
    raw_stop_match_ = 0U;
    decoder_.reset();
    on_stop();
    return;
  } else if (value == kStart) {
    raw_stop_match_ = 1U;
    raw_stop_started_ms_ = now_ms;
  } else {
    raw_stop_match_ = 0U;
  }
  tick(now_ms);
  decoder_.feed(value, now_ms, *this);
  tick(now_ms);
}

void Guard::tick(uint32_t now_ms) {
  now_ms_ = now_ms;
  if (active() && (static_cast<uint32_t>(now_ms - session_started_ms_) >= kSessionLimitMs ||
                   static_cast<uint32_t>(now_ms - transport_deadline_ms_) < 0x80000000UL)) {
    stop(1U, now_ms);
    return;
  }
  if (busy_ && static_cast<uint32_t>(now_ms - operation_deadline_ms_) < 0x80000000UL) {
    stop(2U, now_ms);
    return;
  }
  if (state_ == State::Arming && motion_.arm_ready()) {
    state_ = State::Armed;
    reply(kArm, Result::Accepted);
  }
  decoder_.tick(now_ms, *this);
}

void Guard::stop(uint8_t fault, uint32_t now_ms) {
  static_cast<void>(now_ms);
  motion_.safe_stop();
  state_ = State::Fault;
  fault_ = fault;
  busy_ = false;
}

void Guard::external_fault(uint32_t now_ms) {
  now_ms_ = now_ms;
  if (state_ != State::Fault) stop(3U, now_ms);
}

void Guard::operation_done(bool emit_reply) {
  if (!busy_) return;
  busy_ = false;
  if (emit_reply) reply(kStatus, Result::Accepted);
}

bool Guard::receive_vendor(const VendorAction& action, uint32_t now_ms) {
  now_ms_ = now_ms;
  tick(now_ms);
  if (state_ != State::Armed) return false;
  if (action.size == 3U && action.bytes[1] == 0U) return true;
  if (busy_) return false;
  if (!motion_.execute_vendor(action)) return false;
  busy_ = true;
  operation_deadline_ms_ = now_ms + kOperationLimitMs;
  return true;
}

void Guard::reject(Result result) { reply(kStatus, result); }

void Guard::reply(uint8_t opcode, Result result, uint16_t supply_centivolts) {
  Reply response{};
  response.opcode = reply_opcode(opcode);
  response.result = result;
  response.state = state_;
  response.sequence = sequence_;
  response.remaining_ms = opcode == kSupply ? supply_centivolts :
                          active() ? remaining(now_ms_, transport_deadline_ms_) : 0U;
  response.fault = fault_;
  response.busy = busy_;
  Frame frame{};
  if (encode_reply(response, frame)) replies_.send(frame);
}

void Guard::on_command(const Command& command) {
  if (command.opcode == kBegin) {
    if (!begin_sequence_ok(command) || !motion_.begin_allowed()) {
      reply(command.opcode, Result::WrongState);
      return;
    }
    for (uint8_t index = 0U; index < 8U; ++index) identifier_[index] = command.identifier[index];
    state_ = State::Session;
    session_started_ms_ = now_ms_;
    transport_deadline_ms_ = now_ms_ + kTransportTimeoutMs;
    sequence_ = command.sequence;
    last_accepted_opcode_ = command.opcode;
    motion_.command_accepted(command);
    reply(command.opcode, Result::Accepted);
    return;
  }
  if (command.opcode == kSupply) {
    reply(command.opcode, Result::Accepted, motion_.supply_centivolts());
    return;
  }
  if (command.opcode == kStatus && readonly_status()) {
    reply(command.opcode, Result::Accepted);
    return;
  }
  if (!active()) {
    reply(command.opcode, Result::WrongState);
    return;
  }
  if (static_cast<uint32_t>(now_ms_ - session_started_ms_) >= kSessionLimitMs ||
      static_cast<uint32_t>(now_ms_ - transport_deadline_ms_) < 0x80000000UL) {
    stop(1U, now_ms_);
    reply(command.opcode, Result::Expired);
    return;
  }
  if ((command.opcode == kKeepalive || command.opcode == kStatus) &&
      command.sequence == sequence_ && command.opcode == last_accepted_opcode_) {
    reply(command.opcode, Result::QueryReplay);
    return;
  }
  if (!sequence_ok(command.sequence)) {
    reply(command.opcode, Result::BadSequence);
    return;
  }
  if (command.opcode == kArm) {
    if (state_ != State::Session) reply(command.opcode, Result::WrongState);
    else if (!motion_.metadata_supported()) reply(command.opcode, Result::BadMetadata);
    else if (!motion_.arm_start()) reply(command.opcode, Result::BadMetadata);
    else {
      state_ = State::Arming;
      sequence_ = command.sequence;
      last_accepted_opcode_ = command.opcode;
      motion_.command_accepted(command);
      tick(now_ms_);
    }
  } else if (command.opcode == kKeepalive) {
    sequence_ = command.sequence;
    last_accepted_opcode_ = command.opcode;
    transport_deadline_ms_ = now_ms_ + kTransportTimeoutMs;
    motion_.command_accepted(command);
    reply(command.opcode, Result::Accepted);
  } else if (command.opcode == kExecute) {
    if (state_ != State::Armed) reply(command.opcode, Result::WrongState);
    else if (busy_) reply(command.opcode, Result::Busy);
    else if (!motion_.execute(static_cast<Action>(command.action))) reply(command.opcode, Result::Expired);
    else {
      busy_ = true;
      operation_deadline_ms_ = now_ms_ + kOperationLimitMs;
      sequence_ = command.sequence;
      last_accepted_opcode_ = command.opcode;
      motion_.command_accepted(command);
      reply(command.opcode, Result::Accepted);
    }
  } else if (command.opcode == kStatus) {
    sequence_ = command.sequence;
    last_accepted_opcode_ = command.opcode;
    reply(command.opcode, Result::Accepted);
  } else if (command.opcode == kDisarm) {
    if (state_ != State::Session && state_ != State::Armed) reply(command.opcode, Result::WrongState);
    else if (busy_) reply(command.opcode, Result::Busy);
    else if (!motion_.normal_disarm()) reply(command.opcode, Result::Timeout);
    else {
      sequence_ = command.sequence;
      state_ = State::Disarmed;
      session_started_ms_ = 0U;
      transport_deadline_ms_ = 0U;
      operation_deadline_ms_ = 0U;
      busy_ = false;
      last_accepted_opcode_ = command.opcode;
      motion_.command_accepted(command);
      reply(command.opcode, Result::Accepted);
    }
  } else {
    reply(command.opcode, Result::Unsupported);
  }
}

void Guard::on_stop() {
  stop(4U, now_ms_);
  reply(kStop, Result::Accepted);
}

void Guard::on_frame_error(Result result) {
  if (active()) {
    stop(5U, now_ms_);
    reply(kStatus, result);
    return;
  }
  reply(kStatus, result);
}

Snapshot Guard::snapshot(uint32_t now_ms) const {
  Snapshot result{state_, sequence_, 0U, 0U, busy_, active(), fault_};
  if (active()) result.transport_remaining_ms = remaining(now_ms, transport_deadline_ms_);
  if (busy_) result.operation_remaining_ms = remaining(now_ms, operation_deadline_ms_);
  return result;
}

}
