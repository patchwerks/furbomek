#pragma once

#include "robot_safety/types.h"

namespace robot_safety {

constexpr uint8_t kSync1 = 0xa5;
constexpr uint8_t kSync2 = 0x5a;

class FrameObserver {
 public:
  virtual void on_command(const Command& command) = 0;
  virtual void on_frame_error(FrameError error) = 0;
};

uint16_t crc16_ccitt_false(const uint8_t* bytes, uint8_t length);
bool encode_command(const Command& command, EncodedFrame& frame);
bool encode_reply(const Reply& reply, EncodedFrame& frame);

class FrameDecoder final {
 public:
  FrameDecoder();

  void reset();
  void feed(uint8_t byte, uint32_t now_ms, FrameObserver& observer);
  void tick(uint32_t now_ms, FrameObserver& observer);

 private:
  enum class DecodeState : uint8_t {
    SeekSync1,
    SeekSync2,
    ReadLength,
    Body,
    CrcLow,
    CrcHigh,
  };

  void report(FrameError error, FrameObserver& observer);
  void parse_body(FrameObserver& observer);
  bool timed_out(uint32_t now_ms) const;

  DecodeState state_;
  uint8_t body_[kMaxBodyLength];
  uint8_t body_length_;
  uint8_t body_index_;
  uint8_t crc_low_;
  uint32_t partial_started_ms_;
};

}
