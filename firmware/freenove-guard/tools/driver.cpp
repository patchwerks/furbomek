#include "freenove_guard/dispatcher.h"

#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

namespace {

using namespace freenove_guard;

const char* state_name(State state) {
  switch (state) {
    case State::Boot: return "BOOT";
    case State::Session: return "SESSION";
    case State::Arming: return "ARMING";
    case State::Armed: return "ARMED";
    case State::Fault: return "FAULT";
    case State::Disarmed: return "DISARMED";
  }
  return "UNKNOWN";
}

const char* result_name(Result result) {
  switch (result) {
    case Result::Accepted: return "ACCEPTED";
    case Result::Malformed: return "MALFORMED";
    case Result::BadCrc: return "BAD_CRC";
    case Result::WrongState: return "WRONG_STATE";
    case Result::BadSequence: return "BAD_SEQUENCE";
    case Result::Unsupported: return "UNSUPPORTED";
    case Result::BadMetadata: return "BAD_METADATA";
    case Result::Busy: return "BUSY";
    case Result::Expired: return "EXPIRED";
    case Result::Timeout: return "TIMEOUT";
    case Result::QueryReplay: return "QUERY_REPLAY";
  }
  return "UNKNOWN";
}

struct Motion final : MotionSink {
  bool metadata_supported() const override { return true; }
  uint16_t supply_centivolts() const override { return 818U; }
  bool arm_start() override { std::cout << "MOTION arm-start\n"; return true; }
  bool arm_ready() override { return true; }
  bool normal_disarm() override { std::cout << "MOTION disarm\n"; return true; }
  bool execute(Action action) override {
    std::cout << "MOTION exec=" << static_cast<unsigned>(action) << '\n';
    return true;
  }
  bool execute_vendor(const VendorAction& action) override {
    std::cout << "MOTION vendor=" << static_cast<unsigned>(action.bytes[1]) << '\n';
    return true;
  }
  void safe_stop() override { std::cout << "MOTION safe-stop\n"; }
};

struct Replies final : RoutedReplySink {
  void send(ReplyRoute route, const Frame& frame) override {
    Reply reply{};
    if (!decode_reply(frame, reply)) return;
    const char* destination = route == ReplyRoute::Usb ? "USB" :
                              route == ReplyRoute::RadioComputer ? "RF_COMPUTER" : "RF_MANUAL";
    std::cout << "RADIO robot->" << destination << " result=" << result_name(reply.result)
              << " state=" << state_name(reply.state) << " busy=" << reply.busy;
    if (reply.opcode == 0x35U) std::cout << " centivolts=" << reply.remaining_ms;
    std::cout << '\n';
  }
};

Frame command(uint8_t opcode, uint32_t sequence, uint8_t action = 0U) {
  Command request{opcode, sequence, action, {'r', 'e', 'l', 'a', 'y', '0', '0', '1'}};
  Frame frame{};
  encode_command(request, frame);
  return frame;
}

void relay(Dispatcher& robot, uint8_t source, const Frame& frame, uint32_t now) {
  uint8_t packet[32] = {};
  uint8_t size = 0U;
  if (!wrap_rf(source, frame, packet, size)) return;
  std::cout << "RADIO " << (source == kRfComputerSource ? "computer" : "manual") << "->robot\n";
  robot.receive_radio(packet, size, now);
}

void help() {
  std::cout << "commands: computer begin|arm|keepalive|status|supply|disarm|exec active|sleep|crawl-forward|crawl-backward|crawl-left|crawl-right|turn-left|turn-right, "
               "manual begin|arm|supply|crawl|height|move|twist, done, tick MS, stop, quit\n";
}

}

int main(int argc, char** argv) {
  if (argc == 2 && std::string(argv[1]) == "--help") {
    help();
    return 0;
  }
  if (argc != 1) return 2;
  Motion motion;
  Replies replies;
  Dispatcher robot(motion, replies);
  uint32_t now = 0U;
  help();
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    std::string source;
    input >> source;
    if (source == "quit") break;
    if (source == "tick") {
      uint32_t amount = 0U;
      input >> amount;
      now += amount;
      robot.tick(now);
    } else if (source == "done") {
      robot.operation_done();
    } else if (source == "stop") {
      uint8_t packet[32] = {};
      uint8_t size = 0U;
      make_rf_stop(kRfStopSource, packet, size);
      robot.receive_radio(packet, size, now);
    } else if (source == "computer" || source == "manual") {
      std::string operation;
      input >> operation;
      const uint8_t radio_source = source == "computer" ? kRfComputerSource : kRfManualSource;
      const Snapshot snapshot = robot.snapshot(now);
      if (operation == "begin") relay(robot, radio_source, command(0x28U, 0U), now);
      else if (operation == "arm") relay(robot, radio_source, command(0x2aU, snapshot.sequence + 1U), now);
      else if (operation == "keepalive") relay(robot, radio_source, command(0x2cU, snapshot.sequence + 1U), now);
      else if (operation == "status") relay(robot, radio_source, command(0x32U, snapshot.sequence + 1U), now);
      else if (operation == "supply") relay(robot, radio_source, command(kSupply, snapshot.sequence + 1U), now);
      else if (operation == "disarm") relay(robot, radio_source, command(kDisarm, snapshot.sequence + 1U), now);
      else if (operation == "exec") {
        std::string action;
        input >> action;
        const uint8_t value = action == "active" ? 0U : action == "sleep" ? 1U :
                              action == "crawl-forward" ? 2U : action == "crawl-backward" ? 3U :
                              action == "crawl-left" ? 4U : action == "crawl-right" ? 5U :
                              action == "turn-left" ? 6U : 7U;
        relay(robot, radio_source, command(kExecute, snapshot.sequence + 1U, value), now);
      } else if (source == "manual") {
        Frame action{};
        action.bytes[0] = kStart;
        action.bytes[1] = operation == "height" ? 112U : operation == "move" ? 114U : operation == "twist" ? 118U : 110U;
        action.size = action.bytes[1] == 112U ? 4U : action.bytes[1] == 118U ? 9U : 6U;
        for (uint8_t index = 2U; index < action.size - 1U; ++index) action.bytes[index] = 64U;
        action.bytes[action.size - 1U] = kEnd;
        relay(robot, radio_source, action, now);
      }
    } else {
      std::cout << "ERR command\n";
    }
    std::cout << "STATUS state=" << state_name(robot.snapshot(now).state) << " owner="
              << static_cast<unsigned>(robot.owner()) << '\n';
  }
  return 0;
}
