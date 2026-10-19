#include "freenove_guard/dispatcher.h"
#include "freenove_guard/clock.h"
#include "freenove_guard/esp_diag.h"
#include "freenove_guard/metadata.h"
#include "freenove_guard/scheduler.h"

#include <cassert>
#include <vector>

void test_stop_routes();

namespace {

using namespace freenove_guard;

struct Motion final : MotionSink {
  bool metadata = true;
  bool ready = true;
  uint16_t supply = 818U;
  unsigned arms = 0U;
  unsigned commands = 0U;
  unsigned vendor_commands = 0U;
  unsigned stops = 0U;
  unsigned disarms = 0U;
  unsigned accepted_commands = 0U;
  Action last_action = Action::Active;
  VendorAction last_vendor{};

  bool metadata_supported() const override { return metadata; }
  uint16_t supply_centivolts() const override { return supply; }
  bool arm_start() override { ++arms; return metadata; }
  bool arm_ready() override { return ready; }
  bool normal_disarm() override { ++disarms; return true; }
  bool execute(Action action) override { ++commands; last_action = action; return true; }
  bool execute_vendor(const VendorAction& action) override {
    ++vendor_commands;
    last_vendor = action;
    return true;
  }
  void safe_stop() override { ++stops; }
  void command_accepted(const Command&) override { ++accepted_commands; }
};

struct Replies final : RoutedReplySink {
  ReplyRoute route = ReplyRoute::Usb;
  Frame frame{};
  unsigned count = 0U;
  std::vector<ReplyRoute> routes;
  std::vector<uint8_t> opcodes;

  void send(ReplyRoute next_route, const Frame& next_frame) override {
    route = next_route;
    frame = next_frame;
    ++count;
    routes.push_back(next_route);
    opcodes.push_back(next_frame.bytes[2]);
  }

  Reply reply() const {
    Reply result{};
    assert(decode_reply(frame, result));
    return result;
  }
};

struct TestEspPort final : freenove_guard::EspPort {
  std::vector<uint8_t> input;
  std::vector<uint8_t> output;
  uint8_t available() const override { return static_cast<uint8_t>(input.size()); }
  uint8_t read() override { const uint8_t value = input.front(); input.erase(input.begin()); return value; }
  bool writable(uint8_t) const override { return true; }
  void write(const uint8_t* bytes, uint8_t size) override { output.insert(output.end(), bytes, bytes + size); }
  void inject(const char* text) { while (*text != '\0') input.push_back(static_cast<uint8_t>(*text++)); }
};

Frame command(uint8_t opcode, uint32_t sequence, uint8_t action = 0U) {
  Command request{opcode, sequence, action, {'r', 'e', 'l', 'a', 'y', '0', '0', '1'}};
  Frame frame{};
  assert(encode_command(request, frame));
  return frame;
}

Frame command_with_identifier(uint8_t opcode, uint32_t sequence, const uint8_t* identifier,
                              uint8_t action = 0U) {
  Command request{opcode, sequence, action, {identifier[0], identifier[1], identifier[2], identifier[3],
                                              identifier[4], identifier[5], identifier[6], identifier[7]}};
  Frame frame{};
  assert(encode_command(request, frame));
  return frame;
}

void send_radio(Dispatcher& dispatcher, uint8_t source, const Frame& frame, uint32_t now_ms) {
  uint8_t packet[32] = {};
  uint8_t size = 0U;
  assert(wrap_rf(source, frame, packet, size));
  dispatcher.receive_radio(packet, size, now_ms);
}

void send_usb(Dispatcher& dispatcher, const Frame& frame, uint32_t now_ms) {
  for (uint8_t index = 0U; index < frame.size; ++index) dispatcher.receive_usb(frame.bytes[index], now_ms);
}

void rewrite_reply_crc(Frame& frame) {
  const uint16_t sum = crc16(&frame.bytes[1], 11U);
  frame.bytes[12] = static_cast<uint8_t>(sum & 0x7fU);
  frame.bytes[13] = static_cast<uint8_t>((sum >> 7U) & 0x7fU);
  frame.bytes[14] = static_cast<uint8_t>(sum >> 14U);
}

Frame vendor(uint8_t order, uint8_t size) {
  Frame frame{};
  frame.size = size;
  frame.bytes[0] = kStart;
  frame.bytes[1] = order;
  for (uint8_t index = 2U; index < size - 1U; ++index) frame.bytes[index] = 64U;
  frame.bytes[size - 1U] = kEnd;
  return frame;
}

void begin_and_arm(Dispatcher& dispatcher, Replies& replies, uint8_t source) {
  send_radio(dispatcher, source, command(0x28U, 0U), 0U);
  assert(replies.reply().result == Result::Accepted);
  send_radio(dispatcher, source, command(0x2aU, 1U), 1U);
  dispatcher.tick(1U);
  assert(dispatcher.snapshot(1U).state == State::Armed);
}

}

int main() {
  test_stop_routes();
  assert(metadata_supported(1U, 30U));
  assert(metadata_supported(1U, 31U));
  assert(metadata_supported(1U, 32U));
  assert(!metadata_supported(0U, 30U));
  assert(!metadata_supported(1U, 29U));
  assert(admitted_operation(false, false, false, Action::Active).kind == PendingKind::None);
  assert(admitted_operation(true, true, true, Action::CrawlForward).kind == PendingKind::None);
  assert(admitted_operation(false, true, false, Action::Sleep).action == Action::Sleep);
  Command max_command{kExecute, kMaxSequence, static_cast<uint8_t>(Action::TurnRight),
                      {'r', 'e', 'l', 'a', 'y', '0', '0', '1'}};
  Frame max_frame{};
  assert(encode_command(max_command, max_frame));
  max_command.sequence = kMaxSequence + 1U;
  assert(!encode_command(max_command, max_frame));
  Motion computer_motion;
  Replies computer_replies;
  Dispatcher computer(computer_motion, computer_replies);
  begin_and_arm(computer, computer_replies, kRfComputerSource);
  assert(computer.owner() == LinkOwner::Computer);
  assert(computer_replies.route == ReplyRoute::RadioComputer);
  assert(computer_replies.frame.size == 16U);
  uint8_t reply_packet[32] = {};
  uint8_t reply_size = 0U;
  assert(wrap_rf(kRfRobotSource, computer_replies.frame, reply_packet, reply_size));
  assert(reply_size <= 32U);

  Motion boot_motion;
  Replies boot_replies;
  Dispatcher boot(boot_motion, boot_replies);
  send_radio(boot, kRfComputerSource, command(0x34U, 77U), 0U);
  const Reply boot_supply = boot_replies.reply();
  assert(boot_supply.opcode == 0x35U && boot_supply.result == Result::Accepted);
  assert(boot_supply.state == State::Boot && boot_supply.sequence == 0U && boot_supply.remaining_ms == 818U);
  assert(boot_supply.fault == 0U && !boot_supply.busy);
  assert(boot_replies.frame.bytes[8] == 50U && boot_replies.frame.bytes[9] == 6U);
  assert(boot_replies.route == ReplyRoute::RadioComputer && boot.owner() == LinkOwner::None);
  Reply decoded_reply{};
  Frame invalid_reply = boot_replies.frame;
  invalid_reply.bytes[2] = 0x34U;
  rewrite_reply_crc(invalid_reply);
  assert(!decode_reply(invalid_reply, decoded_reply));
  Reply replay_reply{0x2dU, Result::QueryReplay, State::Armed, 2U, 400U, 0U, false};
  Frame replay_frame{};
  assert(encode_reply(replay_reply, replay_frame));
  assert(decode_reply(replay_frame, decoded_reply) && decoded_reply.result == Result::QueryReplay);
  Frame invalid_replay = replay_frame;
  invalid_replay.bytes[2] = 0x2fU;
  rewrite_reply_crc(invalid_replay);
  assert(!decode_reply(invalid_replay, decoded_reply));
  replay_reply.opcode = 0x2fU;
  assert(!encode_reply(replay_reply, replay_frame));

  const ClockSample first_clock{10U, 100U};
  const ClockSample second_clock{20U, 200U};
  assert(mirror_transport_deadline(60U, first_clock, 450U) == 60U);
  assert(mirror_transport_deadline(60U, second_clock, 400U) == 60U);
  invalid_reply = boot_replies.frame;
  invalid_reply.bytes[10] = 0x80U;
  rewrite_reply_crc(invalid_reply);
  assert(!decode_reply(invalid_reply, decoded_reply));

  send_radio(computer, kRfComputerSource, command(0x2eU, 2U, static_cast<uint8_t>(Action::CrawlForward)), 2U);
  assert(computer_replies.reply().result == Result::Accepted);
  assert(computer.snapshot(2U).busy);
  send_radio(computer, kRfComputerSource, command(0x2eU, 3U, static_cast<uint8_t>(Action::Sleep)), 3U);
  assert(computer_replies.reply().result == Result::Busy);
  send_radio(computer, kRfComputerSource, command(kDisarm, 3U), 3U);
  assert(computer_replies.reply().result == Result::Busy);
  assert(computer.snapshot(3U).state == State::Armed && computer.snapshot(3U).sequence == 2U);
  computer.operation_done();
  assert(computer_replies.reply().opcode == 0x33U);
  assert(!computer_replies.reply().busy);

  Motion disarm_motion;
  Replies disarm_replies;
  Dispatcher disarmed(disarm_motion, disarm_replies);
  begin_and_arm(disarmed, disarm_replies, kRfComputerSource);
  send_radio(disarmed, kRfComputerSource, command(kDisarm, 2U), 2U);
  assert(disarm_replies.reply().opcode == 0x37U && disarm_replies.reply().result == Result::Accepted);
  assert(disarm_replies.reply().state == State::Disarmed && disarmed.owner() == LinkOwner::None);
  assert(disarm_motion.disarms == 1U);
  disarmed.tick(40000U);
  assert(disarmed.snapshot(40000U).state == State::Disarmed);
  send_radio(disarmed, kRfComputerSource, command(kStatus, 999U), 40000U);
  assert(disarm_replies.reply().result == Result::Accepted && disarm_replies.reply().state == State::Disarmed);
  assert(disarm_replies.reply().sequence == 2U);
  send_radio(disarmed, kRfComputerSource, command(kBegin, 0U), 40001U);
  assert(disarm_replies.reply().result == Result::WrongState);
  const uint8_t fresh_id[] = {'r', 'e', 'l', 'a', 'y', '0', '0', '2'};
  send_radio(disarmed, kRfComputerSource, command_with_identifier(kBegin, 3U, fresh_id), 40002U);
  assert(disarm_replies.reply().result == Result::Accepted && disarmed.snapshot(40002U).state == State::Session);
  send_radio(disarmed, kRfComputerSource, command(kArm, 4U), 40003U);
  disarmed.tick(40003U);
  assert(disarmed.snapshot(40003U).state == State::Armed);

  Motion action_motion;
  Replies action_replies;
  Dispatcher actions(action_motion, action_replies);
  begin_and_arm(actions, action_replies, kRfComputerSource);
  for (uint8_t action = 0U; action <= static_cast<uint8_t>(Action::TurnRight); ++action) {
    send_radio(actions, kRfComputerSource, command(kExecute, static_cast<uint32_t>(action) + 2U, action),
               static_cast<uint32_t>(action) + 2U);
    assert(action_replies.reply().result == Result::Accepted);
    assert(static_cast<uint8_t>(action_motion.last_action) == action);
    actions.operation_done();
  }

  Motion retry_motion;
  Replies retry_replies;
  Dispatcher retry(retry_motion, retry_replies);
  begin_and_arm(retry, retry_replies, kRfComputerSource);
  const Frame keepalive = command(kKeepalive, 2U);
  send_radio(retry, kRfComputerSource, keepalive, 100U);
  const Reply keepalive_reply = retry_replies.reply();
  const Snapshot after_keepalive = retry.snapshot(100U);
  const unsigned callbacks_after_keepalive = retry_motion.accepted_commands;
  send_radio(retry, kRfComputerSource, keepalive, 200U);
  const Reply duplicate_keepalive = retry_replies.reply();
  const Snapshot after_duplicate_keepalive = retry.snapshot(200U);
  assert(keepalive_reply.result == Result::Accepted && duplicate_keepalive.result == Result::QueryReplay);
  assert(after_keepalive.sequence == 2U && after_keepalive.transport_remaining_ms == 500U);
  assert(duplicate_keepalive.sequence == 2U && after_duplicate_keepalive.sequence == 2U);
  assert(after_duplicate_keepalive.transport_remaining_ms == 400U);
  assert(retry_motion.accepted_commands == callbacks_after_keepalive);
  assert(duplicate_keepalive.remaining_ms == 400U && duplicate_keepalive.state == State::Armed);

  send_radio(retry, kRfComputerSource, command(kExecute, 3U, static_cast<uint8_t>(Action::Active)), 201U);
  assert(retry_replies.reply().result == Result::Accepted && retry.snapshot(201U).busy);
  send_radio(retry, kRfComputerSource, command(kStatus, 4U), 202U);
  assert(retry_replies.reply().result == Result::Accepted && retry_replies.reply().busy);
  const unsigned callbacks_after_status = retry_motion.accepted_commands;
  retry.operation_done();
  assert(!retry_replies.reply().busy);
  send_radio(retry, kRfComputerSource, command(kStatus, 4U), 203U);
  const Reply duplicate_status = retry_replies.reply();
  assert(duplicate_status.result == Result::QueryReplay && duplicate_status.sequence == 4U);
  assert(!duplicate_status.busy && retry_motion.accepted_commands == callbacks_after_status);
  send_radio(retry, kRfComputerSource, command(kKeepalive, 4U), 204U);
  assert(retry_replies.reply().result == Result::BadSequence);
  send_radio(retry, kRfComputerSource, command(kStatus, 6U), 205U);
  assert(retry_replies.reply().result == Result::BadSequence && retry.snapshot(205U).sequence == 4U);

  Motion expiry_motion;
  Replies expiry_replies;
  Dispatcher expiry(expiry_motion, expiry_replies);
  begin_and_arm(expiry, expiry_replies, kRfComputerSource);
  const Frame expiry_keepalive = command(kKeepalive, 2U);
  send_radio(expiry, kRfComputerSource, expiry_keepalive, 100U);
  send_radio(expiry, kRfComputerSource, expiry_keepalive, 599U);
  assert(expiry_replies.reply().result == Result::QueryReplay);
  expiry.tick(600U);
  assert(expiry.snapshot(600U).state == State::Fault && expiry.snapshot(600U).fault == 1U);
  const unsigned expiry_stops = expiry_motion.stops;
  send_radio(expiry, kRfComputerSource, expiry_keepalive, 601U);
  assert(expiry_replies.reply().result == Result::WrongState);
  assert(expiry.snapshot(601U).state == State::Fault && expiry.snapshot(601U).fault == 1U);
  assert(expiry_motion.stops == expiry_stops);

  Motion parser_motion;
  Replies parser_replies;
  Dispatcher parser_fault(parser_motion, parser_replies);
  begin_and_arm(parser_fault, parser_replies, kRfComputerSource);
  Frame bad_parser_frame = command(kKeepalive, 2U);
  bad_parser_frame.bytes[bad_parser_frame.size - 3U] ^= 1U;
  send_radio(parser_fault, kRfComputerSource, bad_parser_frame, 2U);
  assert(parser_fault.snapshot(2U).state == State::Fault && parser_fault.snapshot(2U).fault == 5U);

  Motion foreign_motion;
  Replies foreign_replies;
  Dispatcher foreign(foreign_motion, foreign_replies);
  begin_and_arm(foreign, foreign_replies, kRfManualSource);
  Frame foreign_malformed = command(kKeepalive, 2U);
  foreign_malformed.bytes[foreign_malformed.size - 3U] ^= 1U;
  send_radio(foreign, kRfComputerSource, foreign_malformed, 2U);
  assert(foreign.snapshot(2U).state == State::Armed && foreign.owner() == LinkOwner::Manual);

  Motion race_motion;
  Replies race_replies;
  Dispatcher race(race_motion, race_replies);
  begin_and_arm(race, race_replies, kRfComputerSource);
  send_radio(race, kRfComputerSource, command(kDisarm, 2U), 2U);
  assert(race.snapshot(2U).state == State::Disarmed);
  uint8_t race_stop[32] = {};
  uint8_t race_stop_size = 0U;
  assert(make_rf_stop(kRfStopSource, race_stop, race_stop_size));
  race.receive_radio(race_stop, race_stop_size, 2U);
  assert(race.snapshot(2U).state == State::Fault && race.snapshot(2U).fault == 4U);

  Motion manual_motion;
  Replies manual_replies;
  Dispatcher manual(manual_motion, manual_replies);
  begin_and_arm(manual, manual_replies, kRfManualSource);
  assert(manual.owner() == LinkOwner::Manual);
  const Frame crawl = vendor(110U, 6U);
  send_radio(manual, kRfManualSource, crawl, 2U);
  assert(manual_motion.vendor_commands == 1U);
  assert(manual_motion.last_vendor.bytes[1] == 110U);
  assert(manual_replies.route == ReplyRoute::RadioManual);
  send_radio(manual, kRfManualSource, vendor(118U, 9U), 3U);
  assert(manual_replies.count == 2U);
  send_radio(manual, kRfManualSource, vendor(0U, 3U), 1000U);
  send_radio(manual, kRfManualSource, vendor(0U, 3U), 2000U);
  send_radio(manual, kRfManualSource, vendor(0U, 3U), 3000U);
  manual.tick(3002U);
  assert(manual.snapshot(3002U).state == State::Fault);
  assert(manual_motion.stops == 1U);

  Motion stop_motion;
  Replies stop_replies;
  Dispatcher stopped(stop_motion, stop_replies);
  uint8_t stop_packet[32] = {};
  uint8_t stop_size = 0U;
  assert(make_rf_stop(kRfStopSource, stop_packet, stop_size));
  assert(stop_size == 6U);
  stopped.receive_radio(stop_packet, stop_size, 0U);
  assert(stopped.snapshot(0U).state == State::Fault);
  assert(stop_motion.stops == 1U);
  send_radio(stopped, kRfManualSource, command(0x34U, 99U), 1U);
  assert(stop_replies.reply().opcode == 0x35U && stop_replies.reply().state == State::Fault);
  assert(stop_replies.reply().result == Result::Accepted && stop_replies.reply().fault == 4U);
  assert(stop_replies.reply().remaining_ms == 818U && !stop_replies.reply().busy);
  assert(stop_replies.route == ReplyRoute::RadioManual);

  Motion query_motion;
  Replies query_replies;
  Dispatcher queried(query_motion, query_replies);
  begin_and_arm(queried, query_replies, kRfManualSource);
  const Snapshot before_query = queried.snapshot(100U);
  send_radio(queried, kRfComputerSource, command(0x34U, 999U), 100U);
  const Reply query_reply = query_replies.reply();
  const Snapshot after_query = queried.snapshot(100U);
  assert(query_reply.opcode == 0x35U && query_reply.result == Result::Accepted);
  assert(query_reply.state == State::Armed && query_reply.sequence == before_query.sequence);
  assert(query_reply.fault == 0U && !query_reply.busy);
  assert(query_reply.remaining_ms == 818U && query_replies.route == ReplyRoute::RadioComputer);
  assert(queried.owner() == LinkOwner::Manual && after_query.sequence == before_query.sequence);
  assert(after_query.transport_remaining_ms == before_query.transport_remaining_ms);
  send_radio(queried, kRfManualSource, command(0x32U, 2U), 101U);
  assert(query_replies.route == ReplyRoute::RadioManual && query_replies.reply().result == Result::Accepted);
  queried.tick(500U);
  assert(queried.snapshot(500U).state == State::Fault);

  Motion pending_motion;
  pending_motion.ready = false;
  Replies pending_replies;
  Dispatcher pending(pending_motion, pending_replies);
  send_radio(pending, kRfManualSource, command(0x28U, 0U), 0U);
  send_radio(pending, kRfManualSource, command(0x2aU, 1U), 1U);
  assert(pending.snapshot(1U).state == State::Arming);
  const Snapshot before_pending_query = pending.snapshot(2U);
  pending_motion.ready = true;
  send_radio(pending, kRfComputerSource, command(0x34U, 0U), 2U);
  assert(pending_replies.count == 3U);
  assert(pending_replies.opcodes[1] == 0x2bU);
  assert(pending_replies.routes[1] == ReplyRoute::RadioManual);
  assert(pending_replies.opcodes[2] == 0x35U);
  assert(pending_replies.routes[2] == ReplyRoute::RadioComputer);
  const Snapshot after_pending_query = pending.snapshot(2U);
  assert(pending.owner() == LinkOwner::Manual && after_pending_query.state == State::Armed);
  assert(after_pending_query.sequence == before_pending_query.sequence);
  assert(after_pending_query.transport_remaining_ms == before_pending_query.transport_remaining_ms);

  Motion ownership_motion;
  Replies ownership_replies;
  Dispatcher ownership(ownership_motion, ownership_replies);
  begin_and_arm(ownership, ownership_replies, kRfManualSource);
  send_radio(ownership, kRfComputerSource, command(0x2eU, 2U, static_cast<uint8_t>(Action::CrawlForward)), 2U);
  assert(ownership_motion.vendor_commands == 0U);
  send_usb(ownership, command(0x2eU, 2U, static_cast<uint8_t>(Action::CrawlForward)), 2U);
  assert(ownership_motion.commands == 0U);
  assert(ownership_replies.route == ReplyRoute::RadioManual);
  assert(ownership_replies.reply().result == Result::WrongState);

  Motion malformed_motion;
  Replies malformed_replies;
  Dispatcher malformed(malformed_motion, malformed_replies);
  const Frame invalid = vendor(80U, 3U);
  send_radio(malformed, kRfManualSource, invalid, 0U);
  assert(malformed_motion.vendor_commands == 0U);
  assert(malformed.snapshot(0U).state == State::Boot);

  const uint8_t orders[] = {0U, 96U, 110U, 112U, 114U, 118U};
  const uint8_t sizes[] = {3U, 3U, 6U, 4U, 6U, 9U};
  for (uint8_t index = 0U; index < sizeof(orders); ++index) {
    VendorAction action{};
    const Frame frame = vendor(orders[index], sizes[index]);
    assert(decode_vendor_action(frame.bytes, frame.size, action));
  }

  TestEspPort port;
  EspDiagnostics esp(port);
  esp.tick(0U, 155U);
  port.inject("OK\n"); esp.tick(1U, 155U); esp.tick(751U, 155U);
  for (uint8_t index = 0U; index < 5U; ++index) { esp.tick(752U + index, 155U); port.inject("OK\n"); esp.tick(753U + index, 155U); }
  esp.tick(760U, 155U);
  assert(esp.ready());
  const uint8_t request[] = {'+', 'I', 'P', 'D', ',', '1', ',', '3', ':', 0x80U, 0U, 0x81U};
  port.input.insert(port.input.end(), request, request + sizeof(request));
  esp.tick(800U, 155U);
  port.inject(">"); esp.tick(801U, 155U);
  assert(port.output.size() >= 3U && port.output[port.output.size() - 3U] == 0x80U &&
         port.output[port.output.size() - 2U] == 1U && port.output.back() == 0x81U);
  return 0;
}
