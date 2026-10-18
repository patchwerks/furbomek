#include "freenove_guard/rf_link.h"

namespace freenove_guard {

bool wrap_rf(uint8_t source, const Frame& frame, uint8_t* packet, uint8_t& size) {
  if (frame.size == 0U || frame.size > 29U || source == 0U) return false;
  packet[0] = kRfMagic;
  packet[1] = source;
  packet[2] = frame.size;
  for (uint8_t index = 0; index < frame.size; ++index) packet[index + 3U] = frame.bytes[index];
  size = static_cast<uint8_t>(frame.size + 3U);
  return true;
}

bool unwrap_rf(const uint8_t* packet, uint8_t size, uint8_t& source, Frame& frame) {
  if (size < 6U || size > 32U || packet[0] != kRfMagic || packet[1] == 0U) return false;
  const uint8_t frame_size = packet[2];
  if (frame_size < 3U || frame_size > 29U || static_cast<uint8_t>(frame_size + 3U) != size) return false;
  source = packet[1];
  frame.size = frame_size;
  for (uint8_t index = 0; index < frame_size; ++index) frame.bytes[index] = packet[index + 3U];
  return frame.bytes[0] == kStart && frame.bytes[frame.size - 1U] == kEnd;
}

bool make_rf_stop(uint8_t source, uint8_t* packet, uint8_t& size) {
  Frame frame{{kStart, kStop, kEnd}, 3U};
  return wrap_rf(source, frame, packet, size);
}

}
