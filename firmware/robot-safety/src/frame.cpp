#include "robot_safety/frame.h"

namespace robot_safety {

namespace {

uint32_t read_u32(const uint8_t* bytes) {
  return static_cast<uint32_t>(bytes[0]) |
         (static_cast<uint32_t>(bytes[1]) << 8U) |
         (static_cast<uint32_t>(bytes[2]) << 16U) |
         (static_cast<uint32_t>(bytes[3]) << 24U);
}

uint16_t read_u16(const uint8_t* bytes) {
  return static_cast<uint16_t>(bytes[0]) | static_cast<uint16_t>(bytes[1] << 8U);
}

void write_u32(uint8_t* bytes, uint32_t value) {
  bytes[0] = static_cast<uint8_t>(value);
  bytes[1] = static_cast<uint8_t>(value >> 8U);
  bytes[2] = static_cast<uint8_t>(value >> 16U);
  bytes[3] = static_cast<uint8_t>(value >> 24U);
}

void write_u16(uint8_t* bytes, uint16_t value) {
  bytes[0] = static_cast<uint8_t>(value);
  bytes[1] = static_cast<uint8_t>(value >> 8U);
}

bool known_opcode(uint8_t raw) {
  return raw >= static_cast<uint8_t>(Opcode::Status) &&
         raw <= static_cast<uint8_t>(Opcode::ClearStopLatch);
}

}

uint16_t crc16_ccitt_false(const uint8_t* bytes, uint8_t length) {
  uint16_t crc = 0xffffU;
  for (uint8_t index = 0; index < length; ++index) {
    crc ^= static_cast<uint16_t>(bytes[index]) << 8U;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000U) != 0 ? static_cast<uint16_t>((crc << 1U) ^ 0x1021U)
                                 : static_cast<uint16_t>(crc << 1U);
    }
  }
  return crc;
}

bool encode_command(const Command& command, EncodedFrame& frame) {
  const uint8_t body_length = command.opcode == Opcode::Lease ? kLeaseBodyLength : kBaseBodyLength;
  if (command.opcode != Opcode::Status && command.opcode != Opcode::Lease &&
      command.opcode != Opcode::Stop && command.opcode != Opcode::ClearStopLatch) {
    return false;
  }
  frame.bytes[0] = kSync1;
  frame.bytes[1] = kSync2;
  frame.bytes[2] = body_length;
  frame.bytes[3] = command.version;
  frame.bytes[4] = static_cast<uint8_t>(command.opcode);
  write_u32(&frame.bytes[5], command.epoch);
  write_u16(&frame.bytes[9], command.sequence);
  if (body_length == kLeaseBodyLength) {
    write_u16(&frame.bytes[11], command.ttl_ms);
  }
  const uint16_t crc = crc16_ccitt_false(&frame.bytes[2], static_cast<uint8_t>(body_length + 1U));
  frame.bytes[3U + body_length] = static_cast<uint8_t>(crc);
  frame.bytes[4U + body_length] = static_cast<uint8_t>(crc >> 8U);
  frame.size = static_cast<uint8_t>(body_length + 5U);
  return true;
}

bool encode_reply(const Reply& reply, EncodedFrame& frame) {
  const uint8_t body_length = 14;
  frame.bytes[0] = kSync1;
  frame.bytes[1] = kSync2;
  frame.bytes[2] = body_length;
  frame.bytes[3] = kProtocolVersion;
  frame.bytes[4] = reply.opcode;
  write_u32(&frame.bytes[5], reply.status.epoch);
  write_u16(&frame.bytes[9], reply.sequence);
  frame.bytes[11] = static_cast<uint8_t>(reply.result);
  frame.bytes[12] = static_cast<uint8_t>(reply.status.state);
  frame.bytes[13] = reply.status.capability_bitmap;
  frame.bytes[14] = reply.status.fault_flags;
  write_u16(&frame.bytes[15], reply.status.lease_remaining_ms);
  const uint16_t crc = crc16_ccitt_false(&frame.bytes[2], body_length + 1U);
  frame.bytes[3U + body_length] = static_cast<uint8_t>(crc);
  frame.bytes[4U + body_length] = static_cast<uint8_t>(crc >> 8U);
  frame.size = static_cast<uint8_t>(body_length + 5U);
  return true;
}

FrameDecoder::FrameDecoder() : state_(DecodeState::SeekSync1), body_{}, body_length_(0), body_index_(0), crc_low_(0), partial_started_ms_(0) {}

void FrameDecoder::reset() {
  state_ = DecodeState::SeekSync1;
  body_length_ = 0;
  body_index_ = 0;
  crc_low_ = 0;
  partial_started_ms_ = 0;
}

bool FrameDecoder::timed_out(uint32_t now_ms) const {
  return state_ != DecodeState::SeekSync1 && static_cast<uint32_t>(now_ms - partial_started_ms_) >= 20U;
}

void FrameDecoder::report(FrameError error, FrameObserver& observer) {
  reset();
  observer.on_frame_error(error);
}

void FrameDecoder::parse_body(FrameObserver& observer) {
  if (body_length_ < kBaseBodyLength) {
    report(FrameError::Malformed, observer);
    return;
  }
  const uint8_t version = body_[0];
  const uint8_t raw_opcode = body_[1];
  const uint32_t epoch = read_u32(&body_[2]);
  const uint16_t sequence = read_u16(&body_[6]);
  if (version == 0 && raw_opcode == static_cast<uint8_t>(Opcode::Stop) &&
      body_length_ == kBaseBodyLength && epoch == 0 && sequence == 0) {
    observer.on_command(Command{0, Opcode::Stop, 0, 0, 0, true});
    reset();
    return;
  }
  if (version != kProtocolVersion) {
    report(FrameError::UnsupportedVersion, observer);
    return;
  }
  if (!known_opcode(raw_opcode)) {
    report(FrameError::UnknownOpcode, observer);
    return;
  }
  const Opcode opcode = static_cast<Opcode>(raw_opcode);
  if ((opcode == Opcode::Lease && body_length_ != kLeaseBodyLength) ||
      (opcode != Opcode::Lease && body_length_ != kBaseBodyLength)) {
    report(FrameError::Malformed, observer);
    return;
  }
  const uint16_t ttl = opcode == Opcode::Lease ? read_u16(&body_[8]) : 0;
  observer.on_command(Command{version, opcode, epoch, sequence, ttl, false});
  reset();
}

void FrameDecoder::feed(uint8_t byte, uint32_t now_ms, FrameObserver& observer) {
  if (timed_out(now_ms)) {
    report(FrameError::PartialTimeout, observer);
  }
  switch (state_) {
    case DecodeState::SeekSync1:
      if (byte == kSync1) {
        state_ = DecodeState::SeekSync2;
        partial_started_ms_ = now_ms;
      }
      break;
    case DecodeState::SeekSync2:
      if (byte == kSync2) {
        state_ = DecodeState::ReadLength;
      } else if (byte == kSync1) {
        partial_started_ms_ = now_ms;
      } else {
        reset();
      }
      break;
    case DecodeState::ReadLength:
      body_length_ = byte;
      if (body_length_ == 0) {
        report(FrameError::Malformed, observer);
        break;
      }
      if (body_length_ > kMaxBodyLength) {
        report(FrameError::Oversized, observer);
        break;
      }
      body_index_ = 0;
      state_ = DecodeState::Body;
      break;
    case DecodeState::Body:
      body_[body_index_] = byte;
      ++body_index_;
      if (body_index_ == body_length_) {
        state_ = DecodeState::CrcLow;
      }
      break;
    case DecodeState::CrcLow:
      crc_low_ = byte;
      state_ = DecodeState::CrcHigh;
      break;
    case DecodeState::CrcHigh: {
      uint8_t crc_input[kMaxBodyLength + 1];
      crc_input[0] = body_length_;
      for (uint8_t index = 0; index < body_length_; ++index) {
        crc_input[index + 1U] = body_[index];
      }
      const uint16_t expected = crc16_ccitt_false(crc_input, static_cast<uint8_t>(body_length_ + 1U));
      const uint16_t received = static_cast<uint16_t>(crc_low_) | static_cast<uint16_t>(byte << 8U);
      if (expected != received) {
        report(FrameError::BadCrc, observer);
      } else {
        parse_body(observer);
      }
      break;
    }
  }
}

void FrameDecoder::tick(uint32_t now_ms, FrameObserver& observer) {
  if (timed_out(now_ms)) {
    report(FrameError::PartialTimeout, observer);
  }
}

}
