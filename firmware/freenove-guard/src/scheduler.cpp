#include "freenove_guard/scheduler.h"

namespace freenove_guard {

PendingOperation admitted_operation(bool terminal_fault, bool guarded_pending, bool vendor_pending,
                                    Action action) {
  if (terminal_fault) return {PendingKind::None, Action::Active};
  if (vendor_pending) return {PendingKind::Vendor, Action::Active};
  if (guarded_pending) return {PendingKind::Guarded, action};
  return {PendingKind::None, Action::Active};
}

}
