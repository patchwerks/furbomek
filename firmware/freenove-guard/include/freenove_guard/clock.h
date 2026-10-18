#pragma once

#include <stdint.h>

namespace freenove_guard {

struct ClockSample {
  uint32_t ticks;
  uint32_t now_ms;
};

inline uint32_t mirror_transport_deadline(uint32_t existing, const ClockSample& sample,
                                          uint16_t remaining_ms) {
  const uint32_t candidate = sample.ticks + (static_cast<uint32_t>(remaining_ms) + 9U) / 10U;
  if (existing == 0U || static_cast<int32_t>(candidate - existing) > 2) return candidate;
  return existing;
}

}
