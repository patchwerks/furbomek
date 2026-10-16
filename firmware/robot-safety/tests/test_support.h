#pragma once

#include "robot_safety/frame.h"
#include "robot_safety/protocol.h"
#include "robot_safety/safety_kernel.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

struct TestContext {
  int checks = 0;

  void require(bool condition, const char* message) {
    ++checks;
    if (!condition) {
      std::fprintf(stderr, "FAIL: %s\n", message);
      std::exit(1);
    }
  }
};

struct EventLog {
  std::vector<int> events;
};

struct RecordingSafeSink final : robot_safety::SafetySink {
  explicit RecordingSafeSink(EventLog* event_log = nullptr) : log(event_log) {}

  void force_safe() override {
    ++safe_calls;
    if (log != nullptr) {
      log->events.push_back(1);
    }
  }

  EventLog* log;
  int safe_calls = 0;
};

struct RecordingReplySink final : robot_safety::ReplySink {
  explicit RecordingReplySink(EventLog* event_log = nullptr) : log(event_log) {}

  bool try_queue(const robot_safety::EncodedFrame& frame) override {
    if (!available || frames.size() >= 32U) {
      return false;
    }
    frames.push_back(frame);
    if (log != nullptr) {
      log->events.push_back(2);
    }
    return true;
  }

  EventLog* log;
  bool available = true;
  std::vector<robot_safety::EncodedFrame> frames;
};

struct TestCommitFaultSignal final : robot_safety::CommitFaultSignal {
  uint8_t enter_commit() override {
    in_commit = true;
    ++enter_count;
    if (inject_before) {
      pending = true;
    }
    return 0;
  }

  void leave_commit(uint8_t saved_status) override {
    static_cast<void>(saved_status);
    in_commit = false;
    ++leave_count;
    if (inject_after) {
      pending = true;
    }
  }

  bool fault_pending() const override { return pending; }

  bool pending = false;
  bool inject_before = false;
  bool inject_after = false;
  bool in_commit = false;
  int enter_count = 0;
  int leave_count = 0;
};

inline robot_safety::Command command(robot_safety::Opcode opcode,
                                     std::uint32_t epoch,
                                     std::uint16_t sequence,
                                     std::uint16_t ttl = 0) {
  return robot_safety::Command{1, opcode, epoch, sequence, ttl, false};
}

inline robot_safety::Command emergency_stop() {
  return robot_safety::Command{0, robot_safety::Opcode::Stop, 0, 0, 0, true};
}

inline robot_safety::EncodedFrame encode(const robot_safety::Command& value) {
  robot_safety::EncodedFrame frame{};
  if (!robot_safety::encode_command(value, frame)) {
    std::fprintf(stderr, "FAIL: command could not be encoded\n");
    std::exit(1);
  }
  return frame;
}

inline void feed(robot_safety::ProtocolEngine& engine,
                 const robot_safety::EncodedFrame& frame,
                 std::uint32_t now) {
  for (std::uint8_t index = 0; index < frame.size; ++index) {
    engine.receive(frame.bytes[index], now);
  }
  engine.tick(now);
}

inline robot_safety::EncodedFrame raw_frame(const std::uint8_t* body,
                                             std::uint8_t body_length) {
  robot_safety::EncodedFrame frame{};
  frame.bytes[0] = robot_safety::kSync1;
  frame.bytes[1] = robot_safety::kSync2;
  frame.bytes[2] = body_length;
  for (std::uint8_t index = 0; index < body_length; ++index) {
    frame.bytes[index + 3U] = body[index];
  }
  const std::uint16_t crc = robot_safety::crc16_ccitt_false(
      &frame.bytes[2], static_cast<std::uint8_t>(body_length + 1U));
  frame.bytes[body_length + 3U] = static_cast<std::uint8_t>(crc);
  frame.bytes[body_length + 4U] = static_cast<std::uint8_t>(crc >> 8U);
  frame.size = static_cast<std::uint8_t>(body_length + 5U);
  return frame;
}

inline bool body_has_result(const robot_safety::EncodedFrame& frame,
                            robot_safety::CommandResult result) {
  return frame.size >= 2U + 1U + 14U + 2U &&
         frame.bytes[2] == 14U &&
         frame.bytes[11] == static_cast<std::uint8_t>(result);
}
