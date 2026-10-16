#pragma once

#include <stdint.h>

namespace robot_safety {

constexpr uint8_t kProtocolVersion = 1;
constexpr uint8_t kMaxBodyLength = 24;
constexpr uint8_t kBaseBodyLength = 8;
constexpr uint8_t kLeaseBodyLength = 10;
constexpr uint8_t kMaxFrameLength = 2 + 1 + kMaxBodyLength + 2;
constexpr uint8_t kCapabilityBitmap = 0;

enum class State : uint8_t {
  StopLatched = 0,
  Disarmed = 1,
  Leased = 2,
};

enum class Opcode : uint8_t {
  Status = 1,
  Lease = 2,
  Stop = 3,
  ClearStopLatch = 4,
};

enum class CommandResult : uint8_t {
  Accepted = 0,
  StateRejected = 1,
  VersionRejected = 2,
  EpochRejected = 3,
  SequenceRejected = 4,
  TtlRejected = 5,
  RateRejected = 6,
  EpochExhausted = 7,
  TransportFault = 8,
};

enum class FrameError : uint8_t {
  Malformed = 1,
  Oversized = 2,
  BadCrc = 3,
  UnknownOpcode = 4,
  UnsupportedVersion = 5,
  PartialTimeout = 6,
};

struct Command {
  uint8_t version;
  Opcode opcode;
  uint32_t epoch;
  uint16_t sequence;
  uint16_t ttl_ms;
  bool emergency_stop;
};

struct StatusSnapshot {
  State state;
  uint32_t epoch;
  uint16_t last_sequence;
  uint16_t lease_remaining_ms;
  uint8_t capability_bitmap;
  uint8_t fault_flags;
  bool epoch_exhausted;
};

struct EncodedFrame {
  uint8_t bytes[kMaxFrameLength];
  uint8_t size;
};

struct Reply {
  uint8_t opcode;
  CommandResult result;
  StatusSnapshot status;
  uint16_t sequence;
};

class SafetySink {
 public:
  virtual void force_safe() = 0;
};

}
