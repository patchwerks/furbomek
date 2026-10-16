#include "robot_safety/protocol.h"

namespace robot_safety {

namespace {

CommandResult frame_error_result(FrameError error) {
  switch (error) {
    case FrameError::Malformed:
    case FrameError::Oversized:
    case FrameError::BadCrc:
    case FrameError::PartialTimeout:
      return CommandResult::StateRejected;
    case FrameError::UnknownOpcode:
      return CommandResult::StateRejected;
    case FrameError::UnsupportedVersion:
      return CommandResult::VersionRejected;
  }
  return CommandResult::StateRejected;
}

}

CommandCommitGuard::CommandCommitGuard(SafetyKernel& kernel,
                                       CommitFaultSignal& signal,
                                       uint32_t now_ms)
    : kernel_(kernel), signal_(signal), now_ms_(now_ms) {}

CommandResult CommandCommitGuard::commit(const Command& command) {
  const uint8_t saved_status = signal_.enter_commit();
  const CommandResult result = signal_.fault_pending()
                                   ? CommandResult::TransportFault
                                   : kernel_.apply(command, now_ms_);
  if (result == CommandResult::TransportFault) {
    kernel_.transport_fault(now_ms_);
  }
  signal_.leave_commit(saved_status);
  return result;
}

ProtocolEngine::ProtocolEngine(SafetySink& safety_sink,
                               ReplySink& reply_sink,
                               CommitFaultSignal& commit_signal)
    : kernel_(safety_sink),
      decoder_(),
      reply_sink_(reply_sink),
      commit_signal_(commit_signal),
      now_ms_(0),
      sticky_transport_fault_(false) {}

void ProtocolEngine::service_fault() {
  if (!sticky_transport_fault_ && commit_signal_.fault_pending()) {
    sticky_transport_fault_ = true;
    decoder_.reset();
    kernel_.transport_fault(now_ms_);
  }
}

void ProtocolEngine::receive(uint8_t byte, uint32_t now_ms) {
  now_ms_ = now_ms;
  service_fault();
  if (!sticky_transport_fault_) {
    kernel_.tick(now_ms);
    decoder_.feed(byte, now_ms, *this);
  }
}

void ProtocolEngine::tick(uint32_t now_ms) {
  now_ms_ = now_ms;
  service_fault();
  kernel_.tick(now_ms);
  if (!sticky_transport_fault_) {
    decoder_.tick(now_ms, *this);
  }
}

void ProtocolEngine::transport_fault(uint32_t now_ms) {
  now_ms_ = now_ms;
  if (!sticky_transport_fault_) {
    sticky_transport_fault_ = true;
    decoder_.reset();
    kernel_.transport_fault(now_ms);
  }
}

bool ProtocolEngine::sticky_transport_fault() const {
  return sticky_transport_fault_;
}

StatusSnapshot ProtocolEngine::snapshot(uint32_t now_ms) const {
  return kernel_.snapshot(now_ms);
}

void ProtocolEngine::queue_reply(uint8_t opcode, uint16_t sequence, CommandResult result) {
  Reply reply{opcode, result, kernel_.snapshot(now_ms_), sequence};
  EncodedFrame frame{};
  if (encode_reply(reply, frame)) {
    reply_sink_.try_queue(frame);
  }
}

void ProtocolEngine::on_command(const Command& command) {
  CommandCommitGuard guard(kernel_, commit_signal_, now_ms_);
  const CommandResult result = guard.commit(command);
  if (result == CommandResult::TransportFault) {
    sticky_transport_fault_ = true;
  }
  queue_reply(static_cast<uint8_t>(command.opcode), command.sequence, result);
  service_fault();
}

void ProtocolEngine::on_frame_error(FrameError error) {
  queue_reply(static_cast<uint8_t>(Opcode::Status), 0, frame_error_result(error));
}

}
