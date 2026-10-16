#include "test_support.h"

namespace {

struct FrameCollector final : robot_safety::FrameObserver {
  void on_command(const robot_safety::Command& value) override {
    ++commands;
    last = value;
  }

  void on_frame_error(robot_safety::FrameError value) override {
    ++errors;
    last_error = value;
  }

  int commands = 0;
  int errors = 0;
  robot_safety::Command last{};
  robot_safety::FrameError last_error = robot_safety::FrameError::Malformed;
};

void feed(robot_safety::FrameDecoder& decoder,
          FrameCollector& collector,
          const robot_safety::EncodedFrame& frame,
          std::uint32_t now) {
  for (std::uint8_t index = 0; index < frame.size; ++index) {
    decoder.feed(frame.bytes[index], now, collector);
  }
}

}

int run_frame_tests(TestContext& test) {
  const int checks_before = test.checks;
  FrameCollector collector;
  robot_safety::FrameDecoder decoder;
  const std::uint8_t crc_vector[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
  test.require(robot_safety::crc16_ccitt_false(crc_vector, 9) == 0x29b1U,
               "crc ccitt false known vector");
  const auto lease = encode(command(robot_safety::Opcode::Lease, 4, 0, 100));
  feed(decoder, collector, lease, 10);
  test.require(collector.commands == 1, "valid lease decoded");
  test.require(collector.last.ttl_ms == 100, "lease ttl decoded");

  auto bad_crc = lease;
  bad_crc.bytes[bad_crc.size - 1U] ^= 0x40U;
  feed(decoder, collector, bad_crc, 11);
  test.require(collector.last_error == robot_safety::FrameError::BadCrc,
               "bad crc rejected");

  auto oversized = robot_safety::EncodedFrame{};
  oversized.size = 5;
  oversized.bytes[0] = robot_safety::kSync1;
  oversized.bytes[1] = robot_safety::kSync2;
  oversized.bytes[2] = 25;
  oversized.bytes[3] = robot_safety::kSync1;
  oversized.bytes[4] = robot_safety::kSync2;
  feed(decoder, collector, oversized, 12);
  test.require(collector.last_error == robot_safety::FrameError::Oversized,
               "oversized body rejected");
  decoder.tick(40, collector);

  FrameCollector short_collector;
  robot_safety::FrameDecoder short_decoder;
  for (std::uint8_t body_length = 1; body_length < robot_safety::kBaseBodyLength; ++body_length) {
    std::uint8_t body[robot_safety::kBaseBodyLength] = {};
    body[0] = robot_safety::kProtocolVersion;
    const int errors_before = short_collector.errors;
    const int commands_before = short_collector.commands;
    feed(short_decoder, short_collector, raw_frame(body, body_length), 50 + body_length);
    test.require(short_collector.commands == commands_before,
                 "short frame cannot produce command");
    test.require(short_collector.errors == errors_before + 1 &&
                     short_collector.last_error == robot_safety::FrameError::Malformed,
                 "short frame rejected at shape boundary");
  }

  auto unknown_opcode = lease;
  unknown_opcode.bytes[4] = 0xee;
  const std::uint16_t unknown_crc = robot_safety::crc16_ccitt_false(
      &unknown_opcode.bytes[2], 1U + unknown_opcode.bytes[2]);
  unknown_opcode.bytes[unknown_opcode.size - 2U] =
      static_cast<std::uint8_t>(unknown_crc & 0xffU);
  unknown_opcode.bytes[unknown_opcode.size - 1U] =
      static_cast<std::uint8_t>(unknown_crc >> 8U);
  feed(decoder, collector, unknown_opcode, 13);
  test.require(collector.last_error == robot_safety::FrameError::UnknownOpcode,
               "unknown opcode rejected");

  auto bad_version = lease;
  bad_version.bytes[3] = 2;
  const std::uint16_t version_crc = robot_safety::crc16_ccitt_false(
      &bad_version.bytes[2], 1U + bad_version.bytes[2]);
  bad_version.bytes[bad_version.size - 2U] =
      static_cast<std::uint8_t>(version_crc & 0xffU);
  bad_version.bytes[bad_version.size - 1U] = static_cast<std::uint8_t>(version_crc >> 8U);
  feed(decoder, collector, bad_version, 14);
  test.require(collector.last_error == robot_safety::FrameError::UnsupportedVersion,
               "unsupported version rejected");

  auto embedded_sync = encode(command(robot_safety::Opcode::Lease, 0xa55aU, 0, 100));
  const int commands_before_embedded = collector.commands;
  feed(decoder, collector, embedded_sync, 15);
  test.require(collector.commands == commands_before_embedded + 1,
               "embedded sync bytes stay in body");

  decoder.feed(robot_safety::kSync1, 0xfffffff0U, collector);
  decoder.feed(robot_safety::kSync2, 0xfffffff0U, collector);
  decoder.feed(6, 0xfffffff1U, collector);
  decoder.feed(1, 0xfffffff2U, collector);
  decoder.tick(0x00000004U, collector);
  test.require(collector.last_error == robot_safety::FrameError::PartialTimeout,
               "partial frame timeout handles millis wrap");

  std::uint32_t random = 0x12345678U;
  const int commands_before_random = collector.commands;
  for (int index = 0; index < 400; ++index) {
    random = random * 1664525U + 1013904223U;
    decoder.feed(static_cast<std::uint8_t>(random >> 24U), 200U + index, collector);
  }
  test.require(collector.commands == commands_before_random,
               "deterministic random stream decodes no ghost command");

  return test.checks - checks_before;
}
