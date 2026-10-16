#include "robot_safety/safety_kernel.h"

namespace robot_safety {

SafetyKernel::SafetyKernel(SafetySink& sink)
    : sink_(sink),
      state_(State::StopLatched),
      epoch_(0),
      last_sequence_(0),
      lease_ttl_ms_(0),
      lease_started_ms_(0),
      last_lease_ms_(0),
      fault_flags_(0),
      lease_active_(false),
      has_last_lease_ms_(false),
      epoch_exhausted_(false) {
  boot();
}

void SafetyKernel::boot() {
  sink_.force_safe();
  state_ = State::StopLatched;
  epoch_ = 0;
  last_sequence_ = 0;
  lease_ttl_ms_ = 0;
  lease_started_ms_ = 0;
  last_lease_ms_ = 0;
  fault_flags_ = 0;
  lease_active_ = false;
  has_last_lease_ms_ = false;
  epoch_exhausted_ = false;
}

bool SafetyKernel::advance_epoch() {
  if (epoch_ == 0xffffffffUL) {
    epoch_exhausted_ = true;
    return false;
  }
  ++epoch_;
  return true;
}

void SafetyKernel::safe_stop() {
  sink_.force_safe();
  if (state_ != State::StopLatched) {
    advance_epoch();
  }
  state_ = State::StopLatched;
  lease_active_ = false;
  has_last_lease_ms_ = false;
  last_sequence_ = 0;
  lease_ttl_ms_ = 0;
}

CommandResult SafetyKernel::apply_lease(const Command& command, uint32_t now_ms) {
  if (state_ == State::StopLatched) {
    return CommandResult::StateRejected;
  }
  if (command.epoch != epoch_) {
    return CommandResult::EpochRejected;
  }
  if (command.ttl_ms < kMinTtlMs || command.ttl_ms > kMaxTtlMs) {
    return CommandResult::TtlRejected;
  }
  if (state_ == State::Disarmed) {
    if (command.sequence != 0) {
      return CommandResult::SequenceRejected;
    }
  } else {
    const uint16_t delta = static_cast<uint16_t>(command.sequence - last_sequence_);
    if (delta == 0 || delta > 32767U) {
      return CommandResult::SequenceRejected;
    }
    if (has_last_lease_ms_ &&
        static_cast<uint32_t>(now_ms - last_lease_ms_) < kRenewalGapMs) {
      return CommandResult::RateRejected;
    }
  }
  state_ = State::Leased;
  lease_active_ = true;
  lease_ttl_ms_ = command.ttl_ms;
  lease_started_ms_ = now_ms;
  last_lease_ms_ = now_ms;
  has_last_lease_ms_ = true;
  last_sequence_ = command.sequence;
  return CommandResult::Accepted;
}

CommandResult SafetyKernel::apply(const Command& command, uint32_t now_ms) {
  const bool emergency = command.emergency_stop ||
                         (command.version == 0 && command.opcode == Opcode::Stop &&
                          command.epoch == 0 && command.sequence == 0 && command.ttl_ms == 0);
  const bool priority_stop = command.version == kProtocolVersion && command.opcode == Opcode::Stop;
  if (!emergency && !priority_stop) {
    tick(now_ms);
  }
  if (emergency || priority_stop) {
    safe_stop();
    return CommandResult::Accepted;
  }
  if ((fault_flags_ & kTransportFault) != 0) {
    return CommandResult::TransportFault;
  }
  if (command.version != kProtocolVersion) {
    return CommandResult::VersionRejected;
  }
  if (command.opcode == Opcode::Status) {
    return CommandResult::Accepted;
  }
  if (command.opcode == Opcode::Lease) {
    return apply_lease(command, now_ms);
  }
  if (command.opcode == Opcode::ClearStopLatch) {
    if (state_ != State::StopLatched) {
      return CommandResult::StateRejected;
    }
    if (command.epoch != epoch_) {
      return CommandResult::EpochRejected;
    }
    if (command.sequence != 0) {
      return CommandResult::SequenceRejected;
    }
    if (!advance_epoch()) {
      return CommandResult::EpochExhausted;
    }
    state_ = State::Disarmed;
    lease_active_ = false;
    has_last_lease_ms_ = false;
    last_sequence_ = 0;
    return CommandResult::Accepted;
  }
  return CommandResult::StateRejected;
}

void SafetyKernel::tick(uint32_t now_ms) {
  if (!lease_active_ || static_cast<uint32_t>(now_ms - lease_started_ms_) < lease_ttl_ms_) {
    return;
  }
  sink_.force_safe();
  lease_active_ = false;
  has_last_lease_ms_ = false;
  last_sequence_ = 0;
  lease_ttl_ms_ = 0;
  if (advance_epoch()) {
    state_ = State::Disarmed;
  } else {
    state_ = State::StopLatched;
  }
}

void SafetyKernel::transport_fault(uint32_t now_ms) {
  static_cast<void>(now_ms);
  fault_flags_ |= kTransportFault;
  safe_stop();
}

uint16_t SafetyKernel::remaining_ms(uint32_t now_ms) const {
  if (!lease_active_) {
    return 0;
  }
  const uint32_t elapsed = now_ms - lease_started_ms_;
  if (elapsed >= lease_ttl_ms_) {
    return 0;
  }
  return static_cast<uint16_t>(lease_ttl_ms_ - elapsed);
}

StatusSnapshot SafetyKernel::snapshot(uint32_t now_ms) const {
  return StatusSnapshot{state_,
                        epoch_,
                        last_sequence_,
                        remaining_ms(now_ms),
                        kCapabilityBitmap,
                        fault_flags_,
                        epoch_exhausted_};
}

}
