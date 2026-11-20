#include "freenove_guard/expressive_motion.h"

#include <assert.h>
#include <algorithm>
#include <cmath>
#include <vector>

namespace {

using freenove_guard::Action;
using freenove_guard::ExpressiveSink;
using freenove_guard::Stance;
using freenove_guard::run_expressive;

constexpr Stance kStanding{{{-81, 99, -15}, {-115, 0, -15}, {-81, -99, -15},
                             {81, 99, -15}, {115, 0, -15}, {81, -99, -15}}};

class Trace final : public ExpressiveSink {
 public:
  std::vector<Stance> moved;
  std::vector<float> speeds;
  std::vector<uint16_t> pauses;
  std::vector<freenove_guard::FootPoint> checked[6];
  unsigned inspected = 0U;
  unsigned reject_target = 0U;
  unsigned interrupt_move = 0U;

  bool reachable(uint8_t leg, const freenove_guard::FootPoint& foot) override {
    if (++inspected == reject_target) return false;
    checked[leg].push_back(foot);
    return true;
  }
  bool move(const Stance& stance, float step_mm) override {
    assert(step_mm > 0.0F && step_mm <= 5.0F);
    for (unsigned leg = 0; leg < 6U; ++leg) {
      const auto& foot = stance.feet[leg];
      assert(std::any_of(checked[leg].begin(), checked[leg].end(), [&](const auto& point) {
        return point.x == foot.x && point.y == foot.y && point.z == foot.z;
      }));
    }
    moved.push_back(stance);
    speeds.push_back(step_mm);
    return moved.size() != interrupt_move;
  }
  bool hold(uint16_t milliseconds) override {
    pauses.push_back(milliseconds);
    return true;
  }
};

void assert_restored(const Stance& stance) {
  for (unsigned index = 0U; index < 6U; ++index) {
    assert(stance.feet[index].x == kStanding.feet[index].x);
    assert(stance.feet[index].y == kStanding.feet[index].y);
    assert(stance.feet[index].z == kStanding.feet[index].z);
  }
}

unsigned nominal_update_ms(const Trace& trace) {
  unsigned duration = 0U;
  Stance previous = kStanding;
  for (unsigned index = 0U; index < trace.moved.size(); ++index) {
    const Stance& goal = trace.moved[index];
    float longest = 0.0F;
    for (unsigned leg = 0U; leg < 6U; ++leg) {
      const auto& from = previous.feet[leg];
      const auto& to = goal.feet[leg];
      const float x = to.x - from.x;
      const float y = to.y - from.y;
      const float z = to.z - from.z;
      longest = std::max(longest, std::sqrt(x * x + y * y + z * z));
    }
    duration += (static_cast<unsigned>(longest / trace.speeds[index]) + 1U) * 20U;
    previous = goal;
  }
  for (uint16_t pause : trace.pauses) duration += pause;
  return duration;
}

void test_footprint_pulse(Action action, float spread_mm, float lower_mm,
                          uint16_t pause_ms, unsigned update_budget_ms) {
  Trace trace;
  assert(run_expressive(action, kStanding, trace));
  assert(trace.inspected == 30U);
  assert(trace.moved.size() == 14U);
  assert(trace.pauses == std::vector<uint16_t>{pause_ms});
  assert(trace.speeds.front() > trace.speeds.back());
  assert(nominal_update_ms(trace) <= update_budget_ms);
  const Stance& peak = trace.moved[6];
  for (unsigned index = 0U; index < 6U; ++index) {
    assert(std::abs(peak.feet[index].x) == std::abs(kStanding.feet[index].x) + spread_mm);
    assert(peak.feet[index].y == kStanding.feet[index].y);
    assert(peak.feet[index].z == kStanding.feet[index].z + lower_mm);
  }
  Stance previous = kStanding;
  for (const Stance& stance : trace.moved) {
    unsigned planted = 0U;
    const float grounded_z = stance.feet[0].z < stance.feet[1].z
                                ? stance.feet[0].z : stance.feet[1].z;
    for (unsigned index = 0U; index < 6U; ++index) {
      const auto& foot = stance.feet[index];
      if (foot.z == grounded_z) ++planted;
      if (foot.x != previous.feet[index].x) {
        assert(foot.z > grounded_z);
        assert(previous.feet[index].z == foot.z);
      }
    }
    assert(planted >= 3U);
    previous = stance;
  }
  assert_restored(trace.moved.back());
}

}

void test_expressive_motion() {
  Trace poke;
  assert(run_expressive(Action::Poke, kStanding, poke));
  assert(poke.inspected == 8U);
  assert(poke.moved.size() == 4U);
  assert(poke.pauses == std::vector<uint16_t>{240U});
  assert(poke.speeds[1] > poke.speeds[2]);
  assert(nominal_update_ms(poke) <= 620U);
  for (unsigned index = 0U; index < 6U; ++index) {
    const auto& foot = poke.moved[1].feet[index];
    assert(foot.x == kStanding.feet[index].x);
    assert(foot.y == kStanding.feet[index].y + (index == 3U ? 17.0F : 0.0F));
    assert(foot.z == kStanding.feet[index].z + (index == 3U ? 14.0F : 0.0F));
  }
  assert_restored(poke.moved.back());

  test_footprint_pulse(Action::DefensiveBrace, 9.0F, 10.0F, 300U, 1080U);
  test_footprint_pulse(Action::TuckPreview, -12.0F, 11.0F, 360U, 1200U);

  Stance resting = kStanding;
  resting.feet[0].z = 0.0F;
  Trace refused;
  assert(!run_expressive(Action::Poke, resting, refused));
  assert(refused.inspected == 0U && refused.moved.empty());

  Trace unreachable;
  unreachable.reject_target = 7U;
  assert(!run_expressive(Action::TuckPreview, kStanding, unreachable));
  assert(unreachable.moved.empty());

  Trace interrupted;
  interrupted.interrupt_move = 2U;
  assert(!run_expressive(Action::DefensiveBrace, kStanding, interrupted));
  assert(interrupted.moved.size() == 2U && interrupted.pauses.empty());
}
