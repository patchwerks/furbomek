#pragma once

#include "robot_safety/types.h"

namespace robot_safety {

class SafetyKernel final {
 public:
  explicit SafetyKernel(SafetySink& sink);

  CommandResult apply(const Command& command, uint32_t now_ms);
  void tick(uint32_t now_ms);
  void transport_fault(uint32_t now_ms);
  StatusSnapshot snapshot(uint32_t now_ms) const;

 private:
  static constexpr uint16_t kMinTtlMs = 50;
  static constexpr uint16_t kMaxTtlMs = 500;
  static constexpr uint16_t kRenewalGapMs = 20;
  static constexpr uint8_t kTransportFault = 1;

  void boot();
  void safe_stop();
  bool advance_epoch();
  CommandResult apply_lease(const Command& command, uint32_t now_ms);
  uint16_t remaining_ms(uint32_t now_ms) const;

  SafetySink& sink_;
  State state_;
  uint32_t epoch_;
  uint16_t last_sequence_;
  uint16_t lease_ttl_ms_;
  uint32_t lease_started_ms_;
  uint32_t last_lease_ms_;
  uint8_t fault_flags_;
  bool lease_active_;
  bool has_last_lease_ms_;
  bool epoch_exhausted_;
};

}
