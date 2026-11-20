#include "freenove_guard/expressive_motion.h"

namespace freenove_guard {
namespace {

constexpr uint8_t kTripodA = 0x15U;
constexpr uint8_t kTripodB = 0x2aU;
constexpr uint8_t kFrontRightIndex = 3U;
constexpr uint8_t kFrontRight = 1U << kFrontRightIndex;
struct Waypoint {
  int8_t spread_a_mm;
  int8_t spread_b_mm;
  uint8_t lifted;
  uint8_t lift_mm;
  int8_t lowered_mm;
  int8_t reach_mm;
  float step_mm;
  uint16_t hold_ms;
};

constexpr Waypoint kPoke[] = {
    {0, 0, kFrontRight, 14, 0, 0, 4.75F, 0},
    {0, 0, kFrontRight, 14, 0, 17, 5.0F, 240},
    {0, 0, kFrontRight, 14, 0, 0, 3.5F, 0},
    {0, 0, 0, 0, 0, 0, 3.25F, 0},
};

template <int8_t Spread, int8_t Lower, uint8_t Lift, uint16_t Pause>
struct FootprintPulse {
  static constexpr Waypoint points[] = {
      {0, 0, 0, 0, Lower, 0, 4.0F, 0},
      {0, 0, kTripodA, Lift, Lower, 0, 4.75F, 0},
      {Spread, 0, kTripodA, Lift, Lower, 0, 4.75F, 0},
      {Spread, 0, 0, 0, Lower, 0, 3.25F, 0},
      {Spread, 0, kTripodB, Lift, Lower, 0, 4.75F, 0},
      {Spread, Spread, kTripodB, Lift, Lower, 0, 4.75F, 0},
      {Spread, Spread, 0, 0, Lower, 0, 3.25F, Pause},
      {Spread, Spread, kTripodB, Lift, Lower, 0, 4.25F, 0},
      {Spread, 0, kTripodB, Lift, Lower, 0, 3.5F, 0},
      {Spread, 0, 0, 0, Lower, 0, 3.25F, 0},
      {Spread, 0, kTripodA, Lift, Lower, 0, 4.25F, 0},
      {0, 0, kTripodA, Lift, Lower, 0, 3.5F, 0},
      {0, 0, 0, 0, Lower, 0, 3.25F, 0},
      {0, 0, 0, 0, 0, 0, 2.75F, 0},
  };
};

template <int8_t Spread, int8_t Lower, uint8_t Lift, uint16_t Pause>
constexpr Waypoint FootprintPulse<Spread, Lower, Lift, Pause>::points[];

bool standing(const Stance& stance) {
  for (uint8_t index = 0; index < 6U; ++index) {
    const FootPoint& foot = stance.feet[index];
    const float outward = index < 3U ? -foot.x : foot.x;
    if (!(outward >= 65.0F && outward <= 175.0F && foot.y >= -130.0F &&
          foot.y <= 130.0F && foot.z >= -18.0F && foot.z <= -12.0F)) {
      return false;
    }
  }
  return true;
}

FootPoint foot_at(FootPoint foot, const Waypoint& waypoint, uint8_t index) {
  const uint8_t bit = static_cast<uint8_t>(1U << index);
  const int8_t spread =
      (bit & kTripodA) != 0U ? waypoint.spread_a_mm : waypoint.spread_b_mm;
  foot.x += (index < 3U ? -1.0F : 1.0F) * static_cast<float>(spread);
  foot.z += static_cast<float>(waypoint.lowered_mm);
  if ((bit & waypoint.lifted) != 0U) foot.z += static_cast<float>(waypoint.lift_mm);
  if (index == kFrontRightIndex) foot.y += static_cast<float>(waypoint.reach_mm);
  return foot;
}

Stance stance_at(const Stance& initial, const Waypoint& waypoint) {
  Stance target{};
  for (uint8_t index = 0; index < 6U; ++index) {
    target.feet[index] = foot_at(initial.feet[index], waypoint, index);
  }
  return target;
}

bool already_checked(const FootPoint* checked, unsigned count, const FootPoint& target) {
  for (unsigned i = 0; i < count; ++i) {
    const FootPoint& point = checked[i];
    if (point.x == target.x && point.y == target.y && point.z == target.z) return true;
  }
  return false;
}

template <unsigned N>
bool run(const Waypoint (&waypoints)[N], const Stance& initial, ExpressiveSink& sink) {
  for (uint8_t leg = 0; leg < 6U; ++leg) {
    FootPoint checked[N];
    unsigned count = 0U;
    for (const Waypoint& waypoint : waypoints) {
      const FootPoint target = foot_at(initial.feet[leg], waypoint, leg);
      if (already_checked(checked, count, target)) continue;
      if (!sink.reachable(leg, target)) return false;
      checked[count++] = target;
    }
  }
  for (const Waypoint& waypoint : waypoints) {
    if (!sink.move(stance_at(initial, waypoint), waypoint.step_mm)) return false;
    if (waypoint.hold_ms != 0U && !sink.hold(waypoint.hold_ms)) return false;
  }
  return true;
}

}

bool run_expressive(Action action, const Stance& initial, ExpressiveSink& sink) {
  if (!standing(initial)) return false;
  switch (action) {
    case Action::Poke:
      return run(kPoke, initial, sink);
    case Action::DefensiveBrace:
      return run(FootprintPulse<9, 10, 9, 300>::points, initial, sink);
    case Action::TuckPreview:
      return run(FootprintPulse<-12, 11, 8, 360>::points, initial, sink);
    default:
      return false;
  }
}

}
