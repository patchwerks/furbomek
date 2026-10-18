#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

bool decode_vendor_action(const uint8_t* bytes, uint8_t size, VendorAction& action);
bool vendor_heartbeat(const VendorAction& action);

}
