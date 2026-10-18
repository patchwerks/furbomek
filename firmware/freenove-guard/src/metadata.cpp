#include "freenove_guard/metadata.h"

namespace freenove_guard {

bool metadata_supported(uint8_t format, uint8_t product) {
  return format == 1U && (product == 30U || product == 31U || product == 32U);
}

}
