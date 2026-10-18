#pragma once

#include <stdint.h>

namespace freenove_guard {

constexpr uint8_t kStart = 0x80;
constexpr uint8_t kEnd = 0x81;
constexpr uint8_t kStop = 0x30;
constexpr uint32_t kTransportTimeoutMs = 500U;
constexpr uint32_t kSessionLimitMs = 30000U;
constexpr uint32_t kOperationLimitMs = 3000U;
constexpr uint32_t kMaxSequence = 0x1fffffUL;

constexpr uint8_t kBegin = 0x28U;
constexpr uint8_t kArm = 0x2aU;
constexpr uint8_t kKeepalive = 0x2cU;
constexpr uint8_t kExecute = 0x2eU;
constexpr uint8_t kStatus = 0x32U;
constexpr uint8_t kSupply = 0x34U;
constexpr uint8_t kDisarm = 0x36U;

enum class State : uint8_t { Boot = 0, Session = 1, Arming = 2, Armed = 3, Fault = 4, Disarmed = 5 };
enum class Action : uint8_t {
  Active = 0,
  Sleep = 1,
  CrawlForward = 2,
  CrawlBackward = 3,
  CrawlLeft = 4,
  CrawlRight = 5,
  TurnLeft = 6,
  TurnRight = 7,
};

enum class Result : uint8_t {
  Accepted = 0,
  Malformed = 1,
  BadCrc = 2,
  WrongState = 3,
  BadSequence = 4,
  Unsupported = 5,
  BadMetadata = 6,
  Busy = 7,
  Expired = 8,
  Timeout = 9,
  QueryReplay = 10,
};

struct Command {
  uint8_t opcode;
  uint32_t sequence;
  uint8_t action;
  uint8_t identifier[8];
};

struct Reply {
  uint8_t opcode;
  Result result;
  State state;
  uint32_t sequence;
  uint16_t remaining_ms;
  uint8_t fault;
  bool busy;
};

struct Frame {
  uint8_t bytes[64];
  uint8_t size;
};

struct Snapshot {
  State state;
  uint32_t sequence;
  uint16_t transport_remaining_ms;
  uint16_t operation_remaining_ms;
  bool busy;
  bool deadlines_active;
  uint8_t fault;
};

struct VendorAction {
  uint8_t bytes[9];
  uint8_t size;
};

class FrameObserver {
 public:
  virtual void on_command(const Command& command) = 0;
  virtual void on_stop() = 0;
  virtual void on_frame_error(Result result) = 0;
};

class ReplySink {
 public:
  virtual void send(const Frame& frame) = 0;
};

class MotionSink {
 public:
  virtual bool metadata_supported() const = 0;
  virtual uint16_t supply_centivolts() const = 0;
  virtual bool begin_allowed() const { return true; }
  virtual bool arm_start() = 0;
  virtual bool arm_ready() = 0;
  virtual bool normal_disarm() = 0;
  virtual bool execute(Action action) = 0;
  virtual bool execute_vendor(const VendorAction&) { return false; }
  virtual void safe_stop() = 0;
  virtual void command_accepted(const Command&) {}
};

}
