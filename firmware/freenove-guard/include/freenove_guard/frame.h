#pragma once

#include "freenove_guard/types.h"

namespace freenove_guard {

uint16_t crc16(const uint8_t* bytes, uint8_t length);
bool valid_readonly_frame(const Frame& frame, uint8_t opcode);
bool encode_command(const Command& command, Frame& frame);
bool encode_reply(const Reply& reply, Frame& frame);
bool decode_reply(const Frame& frame, Reply& reply);

class FrameDecoder final {
 public:
  FrameDecoder();

  void reset();
  void feed(uint8_t value, uint32_t now_ms, FrameObserver& observer);
  void tick(uint32_t now_ms, FrameObserver& observer);

 private:
  enum class State : uint8_t { Seek, Length, Body, Crc0, Crc1, Crc2, End };

  void error(Result result, FrameObserver& observer);
  void parse(FrameObserver& observer);
  bool timed_out(uint32_t now_ms) const;

  State state_;
  uint8_t body_[32];
  uint8_t length_;
  uint8_t index_;
  uint8_t crc_[3];
  uint32_t started_ms_;
};

}
