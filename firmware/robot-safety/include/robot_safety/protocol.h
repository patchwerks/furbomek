#pragma once

#include "robot_safety/frame.h"
#include "robot_safety/safety_kernel.h"

namespace robot_safety {

class ReplySink {
 public:
  virtual bool try_queue(const EncodedFrame& frame) = 0;
};

class CommitFaultSignal {
 public:
  virtual uint8_t enter_commit() = 0;
  virtual void leave_commit(uint8_t saved_status) = 0;
  virtual bool fault_pending() const = 0;
};

class CommandCommitGuard final {
 public:
  CommandCommitGuard(SafetyKernel& kernel, CommitFaultSignal& signal, uint32_t now_ms);

  CommandResult commit(const Command& command);

 private:
  SafetyKernel& kernel_;
  CommitFaultSignal& signal_;
  uint32_t now_ms_;
};

class ProtocolEngine final : public FrameObserver {
 public:
  ProtocolEngine(SafetySink& safety_sink,
                 ReplySink& reply_sink,
                 CommitFaultSignal& commit_signal);

  void receive(uint8_t byte, uint32_t now_ms);
  void tick(uint32_t now_ms);
  void transport_fault(uint32_t now_ms);
  bool sticky_transport_fault() const;
  StatusSnapshot snapshot(uint32_t now_ms) const;

  void on_command(const Command& command) override;
  void on_frame_error(FrameError error) override;

 private:
  void service_fault();
  void queue_reply(uint8_t opcode, uint16_t sequence, CommandResult result);

  SafetyKernel kernel_;
  FrameDecoder decoder_;
  ReplySink& reply_sink_;
  CommitFaultSignal& commit_signal_;
  uint32_t now_ms_;
  bool sticky_transport_fault_;
};

}
