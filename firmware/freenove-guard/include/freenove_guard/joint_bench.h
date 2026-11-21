#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

constexpr uint8_t kFirstJointProbe = 11U;
constexpr uint8_t kJointProbeCount = 108U;
constexpr uint8_t kFirstWideBenchAction = kFirstJointProbe + kJointProbeCount;
constexpr uint8_t kFirstBenchHeight = kFirstWideBenchAction + 48U;
constexpr uint8_t kFirstTableHold = kFirstBenchHeight + 3U;
constexpr uint8_t kFirstTableWalk = kFirstTableHold + 6U;
constexpr uint8_t kAfterLastBenchAction = kFirstTableWalk + 6U;
constexpr uint16_t kTableHoldMs = 5000U;
constexpr uint16_t kTableHoldDeadlineMs = 6500U;
constexpr float kBenchHighFootZ = -25.0F;
constexpr float kBenchLowFootZ = -7.0F;
constexpr float kBenchHeightRoundoffMm = 0.001F;

struct JointProbe {
  uint8_t leg;
  uint8_t axis;
  int8_t offset_deg;
  float step_mm;
};

inline bool bench_action_code(uint8_t code) {
  return code >= kFirstJointProbe && code < kAfterLastBenchAction;
}

inline bool wide_bench_action_code(uint8_t code) {
  return code >= kFirstWideBenchAction && code < kAfterLastBenchAction;
}

inline bool decode_joint_probe(uint8_t code, JointProbe& out) {
  if (code < kFirstJointProbe || code >= kFirstBenchHeight) return false;
  if (wide_bench_action_code(code)) {
    const auto ordinal = static_cast<uint8_t>(code - kFirstWideBenchAction);
    out = {static_cast<uint8_t>(ordinal / 8U),
           static_cast<uint8_t>((ordinal / 4U) % 2U == 0U ? 0U : 2U),
           static_cast<int8_t>((ordinal / 2U) % 2U == 0U ? -36 : 36),
           ordinal % 2U == 0U ? 3.0F : 3.75F};
    return true;
  }
  const uint8_t ordinal = static_cast<uint8_t>(code - kFirstJointProbe);
  const uint8_t joint = ordinal / 6U;
  const int8_t magnitudes[] = {6, 18, 30};
  const int8_t magnitude = magnitudes[ordinal % 3U];
  out = {static_cast<uint8_t>(joint / 3U), static_cast<uint8_t>(joint % 3U),
         static_cast<int8_t>((ordinal / 3U) % 2U == 0U ? -magnitude : magnitude), 3.0F};
  return true;
}

inline bool decode_bench_height(uint8_t code, float& z) {
  if (code < kFirstBenchHeight || code >= kFirstTableHold) return false;
  const float positions[] = {kBenchLowFootZ, -15.0F, kBenchHighFootZ};
  z = positions[code - kFirstBenchHeight];
  return true;
}

inline bool normalize_bench_height_start(float& z) {
  if (!(z >= kBenchHighFootZ - kBenchHeightRoundoffMm &&
        z <= kBenchLowFootZ + kBenchHeightRoundoffMm)) return false;
  if (z < kBenchHighFootZ) z = kBenchHighFootZ;
  if (z > kBenchLowFootZ) z = kBenchLowFootZ;
  return true;
}

inline bool joint_bench_enabled() {
#ifdef FURBOMEK_JOINT_BENCH
  return true;
#else
  return false;
#endif
}

inline uint32_t bench_exec_deadline_ms(uint8_t code) {
  return joint_bench_enabled() && code >= kFirstTableHold && code < kFirstTableWalk
      ? kTableHoldDeadlineMs : kOperationLimitMs;
}

}
