#include "robot_safety/frame.h"
#include "robot_safety/protocol.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

const char* state_name(robot_safety::State state) {
  switch (state) {
    case robot_safety::State::StopLatched:
      return "STOP_LATCHED";
    case robot_safety::State::Disarmed:
      return "DISARMED";
    case robot_safety::State::Leased:
      return "LEASED";
  }
  return "UNKNOWN";
}

const char* result_name(robot_safety::CommandResult result) {
  switch (result) {
    case robot_safety::CommandResult::Accepted:
      return "ACCEPTED";
    case robot_safety::CommandResult::StateRejected:
      return "STATE_REJECTED";
    case robot_safety::CommandResult::VersionRejected:
      return "VERSION_REJECTED";
    case robot_safety::CommandResult::EpochRejected:
      return "EPOCH_REJECTED";
    case robot_safety::CommandResult::SequenceRejected:
      return "SEQUENCE_REJECTED";
    case robot_safety::CommandResult::TtlRejected:
      return "TTL_REJECTED";
    case robot_safety::CommandResult::RateRejected:
      return "RATE_REJECTED";
    case robot_safety::CommandResult::EpochExhausted:
      return "EPOCH_EXHAUSTED";
    case robot_safety::CommandResult::TransportFault:
      return "TRANSPORT_FAULT";
  }
  return "UNKNOWN";
}

struct DiagnosticSafeSink final : robot_safety::SafetySink {
  void force_safe() override { ++calls; }
  std::uint32_t calls = 0;
};

struct ConsoleReplySink final : robot_safety::ReplySink {
  bool try_queue(const robot_safety::EncodedFrame& frame) override {
    if (frame.size < 19U || frame.bytes[2] != 14U) {
      std::printf("REPLY malformed\n");
      return true;
    }
    const auto result = static_cast<robot_safety::CommandResult>(frame.bytes[11]);
    const auto state = static_cast<robot_safety::State>(frame.bytes[12]);
    const std::uint32_t epoch = static_cast<std::uint32_t>(frame.bytes[5]) |
                                 (static_cast<std::uint32_t>(frame.bytes[6]) << 8U) |
                                 (static_cast<std::uint32_t>(frame.bytes[7]) << 16U) |
                                 (static_cast<std::uint32_t>(frame.bytes[8]) << 24U);
    std::printf("REPLY result=%s state=%s epoch=%u capabilities=%u fault=%u remaining=%u\n",
                result_name(result),
                state_name(state),
                static_cast<unsigned>(epoch),
                static_cast<unsigned>(frame.bytes[13]),
                static_cast<unsigned>(frame.bytes[14]),
                static_cast<unsigned>(frame.bytes[15]) |
                    (static_cast<unsigned>(frame.bytes[16]) << 8U));
    return true;
  }
};

struct NativeCommitFaultSignal final : robot_safety::CommitFaultSignal {
  uint8_t enter_commit() override { return 0; }
  void leave_commit(uint8_t saved_status) override { static_cast<void>(saved_status); }
  bool fault_pending() const override { return false; }
};

bool parse_number(const std::string& text, std::uint32_t& value, int base = 10) {
  if (text.empty() || text.front() == '+' || text.front() == '-') {
    return false;
  }
  char* end = nullptr;
  const unsigned long parsed = std::strtoul(text.c_str(), &end, base);
  if (end == text.c_str() || *end != '\0' || parsed > 0xffffffffUL) {
    return false;
  }
  value = static_cast<std::uint32_t>(parsed);
  return true;
}

void send(robot_safety::ProtocolEngine& engine,
          const robot_safety::Command& command,
          std::uint32_t now_ms) {
  robot_safety::EncodedFrame frame{};
  if (!robot_safety::encode_command(command, frame)) {
    std::printf("ERR command-encode\n");
    return;
  }
  for (std::uint8_t index = 0; index < frame.size; ++index) {
    engine.receive(frame.bytes[index], now_ms);
  }
  engine.tick(now_ms);
}

void print_help() {
  std::printf("robot-safety-driver commands:\n");
  std::printf("  status                 send STATUS\n");
  std::printf("  clear                  clear the boot STOP latch\n");
  std::printf("  lease TTL SEQ          acquire or renew a protocol lease\n");
  std::printf("  stop                   send a normal priority STOP\n");
  std::printf("  emergency-stop         send the version-zero emergency STOP\n");
  std::printf("  tick MS                advance monotonic time\n");
  std::printf("  bytes HEX...           feed raw bytes through the decoder\n");
  std::printf("  fault                  latch the sticky transport fault\n");
  std::printf("  quit                   exit\n");
}

}

int main(int argc, char** argv) {
  if (argc == 2 && std::strcmp(argv[1], "--help") == 0) {
    print_help();
    return 0;
  }
  if (argc != 1) {
    std::fprintf(stderr, "usage: robot-safety-driver [--help]\n");
    return 2;
  }
  DiagnosticSafeSink safe_sink;
  ConsoleReplySink reply_sink;
  NativeCommitFaultSignal commit_signal;
  robot_safety::ProtocolEngine engine(safe_sink, reply_sink, commit_signal);
  std::uint32_t now_ms = 0;
  std::printf("READY state=%s epoch=%u capabilities=0\n",
              state_name(engine.snapshot(now_ms).state),
              static_cast<unsigned>(engine.snapshot(now_ms).epoch));
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string operation;
    input >> operation;
    if (operation.empty()) {
      continue;
    }
    if (operation == "help") {
      print_help();
      continue;
    }
    if (operation == "quit") {
      break;
    }
    if (operation == "tick") {
      std::string amount_text;
      std::uint32_t amount = 0;
      if (!(input >> amount_text) || !parse_number(amount_text, amount)) {
        std::printf("ERR tick-argument\n");
        continue;
      }
      now_ms += amount;
      engine.tick(now_ms);
      std::printf("TIME now=%u state=%s\n",
                  static_cast<unsigned>(now_ms),
                  state_name(engine.snapshot(now_ms).state));
      continue;
    }
    if (operation == "fault") {
      engine.transport_fault(now_ms);
      std::printf("FAULT sticky=%u state=%s\n",
                  engine.sticky_transport_fault() ? 1U : 0U,
                  state_name(engine.snapshot(now_ms).state));
      continue;
    }
    if (operation == "bytes") {
      std::string byte_text;
      bool valid = true;
      while (input >> byte_text) {
        std::uint32_t value = 0;
        if (!parse_number(byte_text, value, 16) || value > 255U) {
          valid = false;
          break;
        }
        engine.receive(static_cast<std::uint8_t>(value), now_ms);
      }
      if (!valid) {
        std::printf("ERR byte-argument\n");
      } else {
        engine.tick(now_ms);
      }
      continue;
    }
    const auto status = engine.snapshot(now_ms);
    if (operation == "status") {
      send(engine, robot_safety::Command{1, robot_safety::Opcode::Status, status.epoch, 0, 0, false}, now_ms);
      continue;
    }
    if (operation == "clear") {
      send(engine, robot_safety::Command{1, robot_safety::Opcode::ClearStopLatch, status.epoch, 0, 0, false}, now_ms);
      continue;
    }
    if (operation == "stop") {
      send(engine, robot_safety::Command{1, robot_safety::Opcode::Stop, 0xffffffffUL, 32768, 0, false}, now_ms);
      continue;
    }
    if (operation == "emergency-stop") {
      send(engine, robot_safety::Command{0, robot_safety::Opcode::Stop, 0, 0, 0, true}, now_ms);
      continue;
    }
    if (operation == "lease") {
      std::string ttl_text;
      std::string sequence_text;
      std::uint32_t ttl = 0;
      std::uint32_t sequence = 0;
      if (!(input >> ttl_text >> sequence_text) || !parse_number(ttl_text, ttl) ||
          !parse_number(sequence_text, sequence) || ttl > 65535U || sequence > 65535U) {
        std::printf("ERR lease-argument\n");
        continue;
      }
      send(engine,
           robot_safety::Command{1,
                                  robot_safety::Opcode::Lease,
                                  status.epoch,
                                  static_cast<std::uint16_t>(sequence),
                                  static_cast<std::uint16_t>(ttl),
                                  false},
           now_ms);
      continue;
    }
    std::printf("ERR unknown-command\n");
  }
  return 0;
}
