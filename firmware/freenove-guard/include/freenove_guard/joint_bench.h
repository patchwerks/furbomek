#pragma once

#include <stdint.h>

namespace freenove_guard {

constexpr uint8_t kFirstJointProbe = 11U;
constexpr uint8_t kJointProbeCount = 108U;

struct JointProbe {
  uint8_t leg;
  uint8_t axis;
  int8_t offset_deg;
};

inline bool joint_probe_code(uint8_t code) {
  return code >= kFirstJointProbe &&
         code < static_cast<uint8_t>(kFirstJointProbe + kJointProbeCount);
}

inline bool decode_joint_probe(uint8_t code, JointProbe& out) {
  if (!joint_probe_code(code)) return false;
  const uint8_t ordinal = static_cast<uint8_t>(code - kFirstJointProbe);
  const uint8_t joint = ordinal / 6U;
  const int8_t magnitudes[] = {6, 18, 30};
  const int8_t magnitude = magnitudes[ordinal % 3U];
  out = {static_cast<uint8_t>(joint / 3U), static_cast<uint8_t>(joint % 3U),
         static_cast<int8_t>((ordinal / 3U) % 2U == 0U ? -magnitude : magnitude)};
  return true;
}

inline bool joint_bench_enabled() {
#ifdef FURBOMEK_JOINT_BENCH
  return true;
#else
  return false;
#endif
}

}
