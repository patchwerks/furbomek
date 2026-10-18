#pragma once

#include "freenove_guard/frame.h"

namespace freenove_guard {

class Guard final : public FrameObserver {
 public:
  Guard(MotionSink& motion, ReplySink& replies);

  void receive(uint8_t value, uint32_t now_ms);
  void tick(uint32_t now_ms);
  void operation_done(bool emit_reply = true);
  void external_fault(uint32_t now_ms);
  bool receive_vendor(const VendorAction& action, uint32_t now_ms);
  void reject(Result result);
  Snapshot snapshot(uint32_t now_ms) const;

  void on_command(const Command& command) override;
  void on_stop() override;
  void on_frame_error(Result result) override;

 private:
  void stop(uint8_t fault, uint32_t now_ms);
  void reply(uint8_t opcode, Result result, uint16_t supply_centivolts = 0U);
  bool active() const;
  bool sequence_ok(uint32_t sequence) const;
  bool begin_sequence_ok(const Command& command) const;
  bool readonly_status() const;
  uint16_t remaining(uint32_t now_ms, uint32_t deadline) const;

  MotionSink& motion_;
  ReplySink& replies_;
  FrameDecoder decoder_;
  State state_;
  uint32_t now_ms_;
  uint32_t session_started_ms_;
  uint32_t transport_deadline_ms_;
  uint32_t operation_deadline_ms_;
  uint32_t sequence_;
  uint8_t fault_;
  uint8_t last_accepted_opcode_;
  bool busy_;
  uint8_t identifier_[8];
  uint8_t raw_stop_match_;
  uint32_t raw_stop_started_ms_;
};

}
