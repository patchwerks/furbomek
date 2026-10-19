#include "freenove_guard/dispatcher.h"

#include <cassert>
#include <vector>

namespace {

using namespace freenove_guard;

struct StopMotion final : MotionSink {
  bool ready = true;
  unsigned stops = 0U;
  unsigned executions = 0U;
  bool metadata_supported() const override { return true; }
  uint16_t supply_centivolts() const override { return 800U; }
  bool arm_start() override { return true; }
  bool arm_ready() override { return ready; }
  bool normal_disarm() override { return true; }
  bool execute(Action) override { ++executions; return true; }
  void safe_stop() override { ++stops; }
};

struct RoutedReply {
  ReplyRoute route;
  Reply reply;
};

struct StopReplies final : RoutedReplySink {
  explicit StopReplies(const StopMotion& motion) : motion_(motion) {}
  std::vector<RoutedReply> received;
  void send(ReplyRoute route, const Frame& frame) override {
    Reply reply{};
    assert(decode_reply(frame, reply));
    if (reply.opcode == kStop + 1U) {
      assert(motion_.stops > acknowledged_stops_);
      acknowledged_stops_ = motion_.stops;
      assert(reply.result == Result::Accepted);
      assert(reply.state == State::Fault && reply.fault == 4U && !reply.busy);
    }
    received.push_back({route, reply});
  }
 private:
  const StopMotion& motion_;
  unsigned acknowledged_stops_ = 0U;
};

Frame request(uint8_t opcode, uint32_t sequence) {
  const Command command{opcode, sequence, 0U, {'s', 't', 'o', 'p', 't', 'e', 's', 't'}};
  Frame frame{};
  assert(encode_command(command, frame));
  return frame;
}

void inject(Dispatcher& dispatcher, ReplyRoute route, const Frame& frame) {
  switch (route) {
    case ReplyRoute::Usb:
      for (uint8_t index = 0U; index < frame.size; ++index) {
        dispatcher.receive_usb(frame.bytes[index], 10U);
      }
      break;
    case ReplyRoute::RadioComputer:
    case ReplyRoute::RadioManual: {
      uint8_t packet[32] = {};
      uint8_t size = 0U;
      const uint8_t source = route == ReplyRoute::RadioManual ? kRfManualSource : kRfComputerSource;
      assert(wrap_rf(source, frame, packet, size));
      dispatcher.receive_radio(packet, size, 10U);
      break;
    }
  }
}

void check_stop(ReplyRoute owner_route, ReplyRoute requester, State initial, bool busy) {
  StopMotion motion;
  StopReplies replies(motion);
  Dispatcher dispatcher(motion, replies);
  const Frame stop{{kStart, kStop, kEnd}, 3U};
  if (initial != State::Boot) inject(dispatcher, owner_route, request(kBegin, 0U));
  if (initial == State::Arming || initial == State::Armed || initial == State::Disarmed) {
    motion.ready = initial != State::Arming;
    inject(dispatcher, owner_route, request(kArm, 1U));
  }
  if (busy) inject(dispatcher, owner_route, request(kExecute, 2U));
  if (initial == State::Disarmed) inject(dispatcher, owner_route, request(kDisarm, 2U));
  if (initial == State::Fault) inject(dispatcher, owner_route, stop);
  assert(dispatcher.snapshot(10U).state == initial);
  assert(dispatcher.snapshot(10U).busy == busy);
  const unsigned executions = motion.executions;
  const std::size_t before = replies.received.size();

  inject(dispatcher, requester, stop);

  unsigned stop_acks = 0U;
  for (std::size_t index = before; index < replies.received.size(); ++index) {
    if (replies.received[index].reply.opcode == kStop + 1U) ++stop_acks;
  }
  assert(stop_acks == 1U);
  assert(replies.received.back().reply.opcode == kStop + 1U);
  assert(replies.received.back().route == requester);
  assert(dispatcher.owner() == LinkOwner::None);
  assert(dispatcher.snapshot(10U).state == State::Fault);
  assert(!dispatcher.snapshot(10U).deadlines_active);
  inject(dispatcher, requester, stop);  // Duplicate STOP stays terminal and replies to its requester.
  assert(replies.received.back().reply.opcode == kStop + 1U);
  assert(replies.received.back().route == requester);
  inject(dispatcher, requester, request(kArm, 3U));
  assert(dispatcher.snapshot(10U).state == State::Fault);
  assert(motion.executions == executions);
}

}

void test_stop_routes() {
  using namespace freenove_guard;
  const ReplyRoute routes[] = {ReplyRoute::Usb, ReplyRoute::RadioComputer, ReplyRoute::RadioManual};
  const State states[] = {State::Boot, State::Session, State::Arming, State::Armed,
                          State::Disarmed, State::Fault};
  for (ReplyRoute owner : routes) {
    for (ReplyRoute requester : routes) {
      for (State state : states) check_stop(owner, requester, state, false);
      check_stop(owner, requester, State::Armed, true);
    }
  }

  // A pending ARM reply must still go to its owner, not the STOP requester.
  StopMotion motion;
  motion.ready = false;
  StopReplies replies(motion);
  Dispatcher dispatcher(motion, replies);
  inject(dispatcher, ReplyRoute::RadioManual, request(kBegin, 0U));
  inject(dispatcher, ReplyRoute::RadioManual, request(kArm, 1U));
  const std::size_t before = replies.received.size();
  motion.ready = true;
  uint8_t packet[32] = {};
  uint8_t size = 0U;
  assert(make_rf_stop(kRfStopSource, packet, size));
  dispatcher.receive_radio(packet, size, 10U);
  assert(replies.received.size() == before + 2U);
  assert(replies.received[before].reply.opcode == kArm + 1U);
  assert(replies.received[before].route == ReplyRoute::RadioManual);
  assert(replies.received.back().reply.opcode == kStop + 1U);
  assert(replies.received.back().route == ReplyRoute::RadioComputer);
}
