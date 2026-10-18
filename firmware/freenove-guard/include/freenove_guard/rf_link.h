#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

constexpr uint8_t kRfMagic = 0x52;
constexpr uint8_t kRfComputerSource = 1;
constexpr uint8_t kRfManualSource = 2;
constexpr uint8_t kRfRobotSource = 3;
constexpr uint8_t kRfStopSource = 4;

bool wrap_rf(uint8_t source, const Frame& frame, uint8_t* packet, uint8_t& size);
bool unwrap_rf(const uint8_t* packet, uint8_t size, uint8_t& source, Frame& frame);
bool make_rf_stop(uint8_t source, uint8_t* packet, uint8_t& size);

}
