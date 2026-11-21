#pragma once

#include "freenove_guard/expressive_motion.h"
#include "freenove_guard/joint_bench.h"

namespace freenove_guard {

struct TableMotion {
  float foot_z;
  float step_mm;
  bool walk;
};

inline bool decode_table_motion(uint8_t code, TableMotion& motion) {
  if (code < kFirstTableHold || code >= kAfterLastBenchAction) return false;
  const bool walk = code >= kFirstTableWalk;
  const auto index = static_cast<uint8_t>(code - (walk ? kFirstTableWalk : kFirstTableHold));
  float z = 0.0F;
  if (!decode_bench_height(static_cast<uint8_t>(kFirstBenchHeight + index / 2U), z)) return false;
  motion = {z, index % 2U == 0U ? 3.0F : 3.75F, walk};
  return true;
}

inline Stance table_waypoint(const Stance& initial, float z, uint8_t phase) {
  constexpr float stride = 16.0F;
  constexpr float lift = 6.0F;
  Stance target = initial;
  for (uint8_t i = 0; i < 6U; ++i) {
    auto& foot = target.feet[i];
    foot.z = phase < 3U
        ? foot.z + (z - foot.z) * static_cast<float>(phase + 1U) / 3.0F : z;
    if (phase < 3U) continue;
    const bool first_tripod = i % 2U == 0U;
    if (first_tripod && (phase == 4U || phase == 5U)) foot.y += stride;
    if (!first_tripod && (phase == 6U || phase == 7U)) foot.y -= stride;
    if ((first_tripod && (phase == 3U || phase == 4U)) ||
        (!first_tripod && (phase == 7U || phase == 8U))) foot.z += lift;
  }
  return target;
}

inline bool run_table_motion(const TableMotion& motion, const Stance& initial,
                             ExpressiveSink& sink) {
  float center_z = initial.feet[0].z;
  if (!normalize_bench_height_start(center_z)) return false;
  for (const auto& foot : initial.feet) {
    if (!(foot.z >= center_z - 0.5F && foot.z <= center_z + 0.5F)) return false;
  }
  const uint8_t phases = motion.walk ? 10U : 3U;
  Stance start = initial;
  for (auto& foot : start.feet) foot.z = center_z;
  Stance previous = initial;
  for (uint8_t phase = 0U; phase < phases; ++phase) {
    const Stance target = table_waypoint(start, motion.foot_z, phase);
    for (uint8_t leg = 0U; leg < 6U; ++leg) {
      const auto& a = previous.feet[leg];
      const auto& b = target.feet[leg];
      if ((phase == 0U || a.y != b.y || a.z != b.z) && !sink.reachable(leg, b)) return false;
    }
    previous = target;
  }
  for (uint8_t phase = 0U; phase < phases; ++phase) {
    if (!sink.move(table_waypoint(start, motion.foot_z, phase), motion.step_mm)) return false;
  }
  return sink.hold(motion.walk ? 200U : kTableHoldMs);
}

}
