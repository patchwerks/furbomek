#include "freenove_guard/frame.h"

namespace freenove_guard {

namespace {

uint32_t read21(const uint8_t* bytes) {
  return static_cast<uint32_t>(bytes[0]) |
         (static_cast<uint32_t>(bytes[1]) << 7U) |
         (static_cast<uint32_t>(bytes[2]) << 14U);
}

}

bool valid_readonly_frame(const Frame& frame, uint8_t opcode) {
  if (frame.size != 10U || frame.bytes[0] != kStart || frame.bytes[1] != 4U ||
      frame.bytes[2] != opcode || frame.bytes[9] != kEnd) return false;
  for (uint8_t index = 1U; index < 9U; ++index) {
    if (frame.bytes[index] >= 128U) return false;
  }
  const uint16_t expected = crc16(&frame.bytes[1], 5U);
  const uint16_t received = static_cast<uint16_t>(frame.bytes[6]) |
                            static_cast<uint16_t>(frame.bytes[7] << 7U) |
                            static_cast<uint16_t>(frame.bytes[8] << 14U);
  return expected == received && frame.bytes[8] <= 3U;
}

bool decode_reply(const Frame& frame, Reply& reply) {
  if (frame.size != 16U || frame.bytes[0] != kStart || frame.bytes[1] != 10U ||
      frame.bytes[15] != kEnd) return false;
  for (uint8_t index = 1U; index < 15U; ++index) {
    if (frame.bytes[index] >= 128U) return false;
  }
  const uint16_t expected = crc16(&frame.bytes[1], 11U);
  const uint16_t received = static_cast<uint16_t>(frame.bytes[12]) |
                            static_cast<uint16_t>(frame.bytes[13] << 7U) |
                            static_cast<uint16_t>(frame.bytes[14] << 14U);
  const bool query_replay = frame.bytes[3] == static_cast<uint8_t>(Result::QueryReplay) &&
                            (frame.bytes[2] == static_cast<uint8_t>(kKeepalive + 1U) ||
                             frame.bytes[2] == static_cast<uint8_t>(kStatus + 1U));
  if (expected != received || frame.bytes[2] < 0x29U || frame.bytes[2] > 0x37U ||
      (frame.bytes[2] & 1U) == 0U || frame.bytes[14] > 3U ||
      (frame.bytes[3] > static_cast<uint8_t>(Result::Timeout) && !query_replay) ||
      (frame.bytes[3] == static_cast<uint8_t>(Result::QueryReplay) && !query_replay) ||
      frame.bytes[4] > 5U ||
      frame.bytes[11] > 1U) return false;
  reply.opcode = frame.bytes[2];
  reply.result = static_cast<Result>(frame.bytes[3]);
  reply.state = static_cast<State>(frame.bytes[4]);
  reply.sequence = read21(&frame.bytes[5]);
  reply.remaining_ms = static_cast<uint16_t>(frame.bytes[8]) |
                       static_cast<uint16_t>(frame.bytes[9] << 7U);
  reply.fault = frame.bytes[10];
  reply.busy = frame.bytes[11] != 0U;
  return true;
}

}
