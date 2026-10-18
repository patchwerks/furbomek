#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

enum class PendingKind : uint8_t { None = 0, Guarded = 1, Vendor = 2 };

struct PendingOperation {
  PendingKind kind;
  Action action;
};

PendingOperation admitted_operation(bool terminal_fault, bool guarded_pending, bool vendor_pending,
                                    Action action);

}
