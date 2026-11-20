#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

struct FootPoint {
  float x;
  float y;
  float z;
};

struct Stance {
  FootPoint feet[6];
};

class ExpressiveSink {
 public:
  virtual bool reachable(uint8_t leg_index, const FootPoint& foot) = 0;
  virtual bool move(const Stance& stance, float step_mm) = 0;
  virtual bool hold(uint16_t milliseconds) = 0;

 protected:
  ~ExpressiveSink() = default;
};

bool run_expressive(Action action, const Stance& initial, ExpressiveSink& sink);

}
