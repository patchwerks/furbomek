#include "freenove_guard/frame.h"

namespace freenove_guard {

namespace {

uint32_t read21(const uint8_t* bytes) {
  return static_cast<uint32_t>(bytes[0]) |
         (static_cast<uint32_t>(bytes[1]) << 7U) |
         (static_cast<uint32_t>(bytes[2]) << 14U);
}

void write21(uint8_t* bytes, uint32_t value) {
  bytes[0] = static_cast<uint8_t>(value & 0x7fU);
  bytes[1] = static_cast<uint8_t>((value >> 7U) & 0x7fU);
  bytes[2] = static_cast<uint8_t>((value >> 14U) & 0x7fU);
}

void write14(uint8_t* bytes, uint16_t value) {
  bytes[0] = static_cast<uint8_t>(value & 0x7fU);
  bytes[1] = static_cast<uint8_t>((value >> 7U) & 0x7fU);
}

void write_id(uint8_t* output, const uint8_t* input) {
  for (uint8_t index = 0; index < 8U; ++index) {
    output[index * 2U] = static_cast<uint8_t>(input[index] & 0x7fU);
    output[index * 2U + 1U] = static_cast<uint8_t>(input[index] >> 7U);
  }
}

void read_id(uint8_t* output, const uint8_t* input) {
  for (uint8_t index = 0; index < 8U; ++index) {
    output[index] = static_cast<uint8_t>(input[index * 2U] |
                                         static_cast<uint8_t>(input[index * 2U + 1U] << 7U));
  }
}

bool command_shape(const Command& command, uint8_t& length) {
  if (command.opcode == kBegin) {
    length = 20U;
    return true;
  }
  if (command.opcode == kExecute) {
    length = 5U;
    return command.action <= static_cast<uint8_t>(Action::TurnRight);
  }
  if (command.opcode == kArm || command.opcode == kKeepalive || command.opcode == kStatus ||
      command.opcode == kSupply || command.opcode == kDisarm) {
    length = 4U;
    return true;
  }
  return false;
}

}

uint16_t crc16(const uint8_t* bytes, uint8_t length) {
  uint16_t crc = 0xffffU;
  for (uint8_t index = 0; index < length; ++index) {
    crc ^= static_cast<uint16_t>(bytes[index]) << 8U;
    for (uint8_t bit = 0; bit < 8U; ++bit) {
      crc = (crc & 0x8000U) != 0U ? static_cast<uint16_t>((crc << 1U) ^ 0x1021U)
                                  : static_cast<uint16_t>(crc << 1U);
    }
  }
  return crc;
}

bool encode_command(const Command& command, Frame& frame) {
  uint8_t length = 0;
  if (!command_shape(command, length) || command.sequence > kMaxSequence) {
    return false;
  }
  frame.bytes[0] = kStart;
  frame.bytes[1] = length;
  frame.bytes[2] = command.opcode;
  write21(&frame.bytes[3], command.sequence);
  if (command.opcode == 0x28U) {
    write_id(&frame.bytes[6], command.identifier);
  } else if (command.opcode == 0x2eU) {
    frame.bytes[6] = command.action;
  }
  const uint16_t sum = crc16(&frame.bytes[1], static_cast<uint8_t>(length + 1U));
  frame.bytes[2U + length] = static_cast<uint8_t>(sum & 0x7fU);
  frame.bytes[3U + length] = static_cast<uint8_t>((sum >> 7U) & 0x7fU);
  frame.bytes[4U + length] = static_cast<uint8_t>(sum >> 14U);
  frame.bytes[5U + length] = kEnd;
  frame.size = static_cast<uint8_t>(length + 6U);
  return true;
}

bool encode_reply(const Reply& reply, Frame& frame) {
  const bool query_replay = reply.result == Result::QueryReplay &&
                            (reply.opcode == static_cast<uint8_t>(kKeepalive + 1U) ||
                             reply.opcode == static_cast<uint8_t>(kStatus + 1U));
  if (reply.opcode < 0x29U || reply.opcode > 0x37U || (reply.opcode & 1U) == 0U ||
      static_cast<uint8_t>(reply.state) > static_cast<uint8_t>(State::Disarmed) ||
      (static_cast<uint8_t>(reply.result) > static_cast<uint8_t>(Result::Timeout) && !query_replay) ||
      (reply.result == Result::QueryReplay && !query_replay) ||
      reply.sequence > kMaxSequence || reply.remaining_ms > 0x3fffU || reply.fault > 0x7fU) {
    return false;
  }
  const uint8_t length = 10U;
  frame.bytes[0] = kStart;
  frame.bytes[1] = length;
  frame.bytes[2] = reply.opcode;
  frame.bytes[3] = static_cast<uint8_t>(reply.result);
  frame.bytes[4] = static_cast<uint8_t>(reply.state);
  write21(&frame.bytes[5], reply.sequence);
  write14(&frame.bytes[8], reply.remaining_ms);
  frame.bytes[10] = reply.fault & 0x7fU;
  frame.bytes[11] = reply.busy ? 1U : 0U;
  const uint16_t sum = crc16(&frame.bytes[1], static_cast<uint8_t>(length + 1U));
  frame.bytes[2U + length] = static_cast<uint8_t>(sum & 0x7fU);
  frame.bytes[3U + length] = static_cast<uint8_t>((sum >> 7U) & 0x7fU);
  frame.bytes[4U + length] = static_cast<uint8_t>(sum >> 14U);
  frame.bytes[5U + length] = kEnd;
  frame.size = static_cast<uint8_t>(length + 6U);
  return true;
}
FrameDecoder::FrameDecoder() { reset(); }

void FrameDecoder::reset() {
  state_ = State::Seek;
  length_ = 0;
  index_ = 0;
  crc_[0] = crc_[1] = crc_[2] = 0;
  started_ms_ = 0;
}

bool FrameDecoder::timed_out(uint32_t now_ms) const {
  return state_ != State::Seek && static_cast<uint32_t>(now_ms - started_ms_) >= 50U;
}

void FrameDecoder::error(Result result, FrameObserver& observer) {
  reset();
  observer.on_frame_error(result);
}

void FrameDecoder::parse(FrameObserver& observer) {
  if (length_ < 4U || length_ > 20U) {
    error(Result::Malformed, observer);
    return;
  }
  Command command{};
  command.opcode = body_[0];
  command.sequence = read21(&body_[1]);
  command.action = 0;
  for (uint8_t index = 0; index < 8U; ++index) command.identifier[index] = 0;
  if (command.opcode == kBegin && length_ == 20U) {
    for (uint8_t index = 0; index < 8U; ++index) {
      if (body_[5U + index * 2U] > 1U) {
        error(Result::Malformed, observer);
        return;
      }
    }
    read_id(command.identifier, &body_[4]);
  } else if (command.opcode == kExecute && length_ == 5U) {
    if (body_[4] > static_cast<uint8_t>(Action::TurnRight)) {
      error(Result::Unsupported, observer);
      return;
    }
    command.action = body_[4];
  } else if ((command.opcode == kArm || command.opcode == kKeepalive || command.opcode == kStatus ||
              command.opcode == kSupply || command.opcode == kDisarm) &&
             length_ == 4U) {
  } else {
    error(Result::Malformed, observer);
    return;
  }
  observer.on_command(command);
  reset();
}

void FrameDecoder::feed(uint8_t value, uint32_t now_ms, FrameObserver& observer) {
  if (timed_out(now_ms)) error(Result::Expired, observer);
  switch (state_) {
    case State::Seek:
      if (value == kStart) {
        state_ = State::Length;
        started_ms_ = now_ms;
      }
      break;
    case State::Length:
      length_ = value;
      if (value == 0U || value > 32U || value >= 128U) error(Result::Malformed, observer);
      else {
        index_ = 0;
        state_ = State::Body;
      }
      break;
    case State::Body:
      if (value >= 128U || index_ >= sizeof(body_)) error(Result::Malformed, observer);
      else {
        body_[index_++] = value;
        if (index_ == length_) state_ = State::Crc0;
      }
      break;
    case State::Crc0:
      if (value >= 128U) error(Result::Malformed, observer);
      else {
        crc_[0] = value;
        state_ = State::Crc1;
      }
      break;
    case State::Crc1:
      if (value >= 128U) error(Result::Malformed, observer);
      else {
        crc_[1] = value;
        state_ = State::Crc2;
      }
      break;
    case State::Crc2:
      if (value >= 128U) error(Result::Malformed, observer);
      else if (value > 3U) error(Result::Malformed, observer);
      else {
        crc_[2] = value;
        state_ = State::End;
      }
      break;
    case State::End:
      if (value != kEnd) error(Result::Malformed, observer);
      else {
        uint8_t crc_input[33];
        crc_input[0] = length_;
        for (uint8_t index = 0; index < length_; ++index) crc_input[index + 1U] = body_[index];
        const uint16_t expected = crc16(crc_input, static_cast<uint8_t>(length_ + 1U));
        const uint16_t received = static_cast<uint16_t>(crc_[0]) |
                                  static_cast<uint16_t>(crc_[1] << 7U) |
                                  static_cast<uint16_t>(crc_[2] << 14U);
        if (expected != received) error(Result::BadCrc, observer);
        else parse(observer);
      }
      break;
  }
}

void FrameDecoder::tick(uint32_t now_ms, FrameObserver& observer) {
  if (timed_out(now_ms)) error(Result::Expired, observer);
}

}
