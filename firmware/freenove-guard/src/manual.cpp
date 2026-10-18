#include "freenove_guard/manual.h"

namespace freenove_guard {

namespace {

uint8_t expected_size(uint8_t order) {
  switch (order) {
    case 0U:
    case 96U: return 3U;
    case 112U: return 4U;
    case 110U:
    case 114U: return 6U;
    case 118U: return 9U;
    default: return 0U;
  }
}

}

bool decode_vendor_action(const uint8_t* bytes, uint8_t size, VendorAction& action) {
  if (size < 3U || size != expected_size(bytes[1]) || bytes[0] != kStart ||
      bytes[size - 1U] != kEnd) return false;
  for (uint8_t index = 1U; index < size - 1U; ++index) {
    if (bytes[index] >= 128U) return false;
  }
  action.size = size;
  for (uint8_t index = 0U; index < size; ++index) action.bytes[index] = bytes[index];
  return true;
}

bool vendor_heartbeat(const VendorAction& action) {
  return action.size == 3U && action.bytes[1] == 0U;
}

}
