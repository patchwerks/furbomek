// Offline fixture only: real Guard/Dispatcher, virtual time, no device adapters.
#include "freenove_guard/dispatcher.h"

#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
using namespace freenove_guard;
unsigned checks = 0U;
void require(bool value, const char* label) {
  ++checks;
  if (!value) { std::fprintf(stderr, "FAIL: %s\n", label); std::exit(1); }
}
struct Motion final : MotionSink {
  unsigned executions = 0U;
  unsigned stops = 0U;
  unsigned disarms = 0U;
  bool metadata_supported() const override { return true; }
  uint16_t supply_centivolts() const override { return 800U; }
  bool arm_start() override { return true; }
  bool arm_ready() override { return true; }
  bool normal_disarm() override { ++disarms; return true; }
  bool execute(Action) override { ++executions; return true; }
  void safe_stop() override { ++stops; }
};
struct Replies final : RoutedReplySink {
  explicit Replies(Motion& motion) : motion_(motion) {}
  Motion& motion_;
  bool drop = false;
  unsigned stop_callbacks_at_ack = 0U;
  Reply last{};
  ReplyRoute route = ReplyRoute::Usb;
  void send(ReplyRoute source, const Frame& frame) override {
    if (drop) return;
    require(decode_reply(frame, last), "real reply decodes");
    route = source;
    if (last.opcode == kStop + 1U) stop_callbacks_at_ack = motion_.stops;
  }
};
Frame frame(uint8_t opcode, uint32_t seq, uint8_t action = 0U, uint8_t session = 1U) {
  const Command command{opcode, seq, action, {'t', 'e', 's', 't', '0', '0', '0', session}};
  Frame result{};
  require(encode_command(command, result), "fixture command encodes");
  return result;
}
struct Fixture {
  Motion motion;
  Replies replies{motion};
  Dispatcher dispatcher{motion, replies};
  void deliver(const Frame& value, uint32_t time) {
    uint8_t packet[32]{};
    uint8_t size = 0U;
    require(wrap_rf(kRfComputerSource, value, packet, size), "real RF envelope encodes");
    dispatcher.receive_radio(packet, size, time);
    dispatcher.tick(time);
  }
  void start(uint32_t time = 0U) {
    deliver(frame(kBegin, 0U), time);
    deliver(frame(kArm, 1U), time);
    require(dispatcher.snapshot(time).state == State::Armed, "fixture armed in memory only");
  }
  void stop(uint32_t time) {
    dispatcher.receive_usb(kStart, time);
    dispatcher.receive_usb(kStop, time);
    dispatcher.receive_usb(kEnd, time);
  }
};
void report(const char* name, unsigned before) {
  std::printf("%s: %u checks passed\n", name, checks - before);
}
void require_terminal(Fixture& f, uint32_t time, uint32_t sequence,
                      uint8_t fault, unsigned executions) {
  const Snapshot snapshot = f.dispatcher.snapshot(time);
  require(snapshot.state == State::Fault, "recovery attempt preserves terminal Fault");
  require(snapshot.fault == fault, "recovery attempt preserves fault reason");
  require(snapshot.sequence == sequence, "recovery attempt preserves accepted sequence");
  require(!snapshot.busy && !snapshot.deadlines_active, "terminal fault has no active work or lease");
  require(f.dispatcher.owner() == LinkOwner::None, "recovery attempt cannot acquire ownership");
  require(f.motion.executions == executions, "recovery attempt never executes or auto-resumes");
  require(f.motion.disarms == 0U, "terminal fault never invokes normal disarm");
}
void stop_and_cancellation() {
  const unsigned before = checks;
  for (uint32_t cancelled_at : {1U, 249U, 499U, 500U}) {
    Fixture f;
    f.start();
    f.deliver(frame(kExecute, 2U), 0U);
    f.replies.drop = true;  // Lost ACK does not suppress local STOP.
    const unsigned stops_before_cancel = f.motion.stops;
    f.stop(cancelled_at);
    require(f.motion.stops > stops_before_cancel, "first STOP invokes safe callback despite lost ACK");
    require(f.dispatcher.snapshot(cancelled_at).state == State::Fault, "cancel reaches terminal fault");
    require(!f.dispatcher.snapshot(cancelled_at).busy, "cancel clears pending work");
    f.replies.drop = false;
    f.stop(cancelled_at + 1U);
    require(f.replies.route == ReplyRoute::Usb, "STOP ACK follows requester, not RF owner");
    require(f.replies.stop_callbacks_at_ack > 0U &&
                f.replies.stop_callbacks_at_ack == f.motion.stops, "safe callback precedes STOP ACK");
    require(f.dispatcher.owner() == LinkOwner::None, "STOP releases ownership");
    const unsigned executions = f.motion.executions;
    require_terminal(f, cancelled_at + 1U, 2U, 4U, executions);
    f.dispatcher.operation_done();  // Late completion after cancellation.
    require_terminal(f, cancelled_at + 1U, 2U, 4U, executions);
    f.deliver(frame(kExecute, 3U), cancelled_at + 2U);
    require(f.replies.last.result == Result::WrongState, "late execute rejected in Fault");
    require_terminal(f, cancelled_at + 2U, 2U, 4U, executions);
    // Rejected commands do not consume sequence 3. Use the exact next sequence
    // and a fresh session so a sequence/session error cannot mask Fault recovery.
    f.deliver(frame(kBegin, 3U, 0U, 2U), cancelled_at + 3U);
    require(f.replies.last.result == Result::WrongState, "exact-next BEGIN after STOP rejected");
    require_terminal(f, cancelled_at + 3U, 2U, 4U, executions);
    f.deliver(frame(kDisarm, 3U), cancelled_at + 4U);
    require(f.replies.last.result == Result::WrongState, "exact-next DISARM after STOP rejected");
    require_terminal(f, cancelled_at + 4U, 2U, 4U, executions);
    f.dispatcher.tick(cancelled_at + 1000U);
    require_terminal(f, cancelled_at + 1000U, 2U, 4U, executions);
  }
  report("stop-cancellation-late-completion", before);
}
void latency_and_loss() {
  const unsigned before = checks;
  for (uint32_t arrival : {499U, 500U, 501U}) {
    Fixture f;
    f.start();
    f.deliver(frame(kKeepalive, 2U), arrival);
    const bool timely = arrival < kTransportTimeoutMs;
    require((f.dispatcher.snapshot(arrival).state == State::Armed) == timely,
            "heartbeat must arrive strictly before deadline");
    if (timely) {
      f.dispatcher.tick(arrival + kTransportTimeoutMs - 1U);
      require(f.motion.stops == 0U, "no early expiry");
      f.dispatcher.tick(arrival + kTransportTimeoutMs);
      require(f.motion.stops == 1U, "dropped next heartbeat expires exactly");
    } else {
      require(f.motion.stops >= 1U, "late heartbeat does not revive fault");
    }
  }
  Fixture wrap;
  const uint32_t start = 0xffffff00U;
  wrap.start(start);
  wrap.dispatcher.tick(start + kTransportTimeoutMs - 1U);
  require(wrap.dispatcher.snapshot(start + 499U).state == State::Armed, "wrap before deadline");
  wrap.dispatcher.tick(start + kTransportTimeoutMs);
  require(wrap.dispatcher.snapshot(start + 500U).state == State::Fault, "wrap exact deadline");
  report("virtual-latency-loss-and-clock-wrap", before);
}
void query_replay() {
  const unsigned before = checks;
  Fixture f;
  f.start();
  f.deliver(frame(kKeepalive, 2U), 100U);
  f.deliver(frame(kKeepalive, 2U), 599U);
  require(f.replies.last.result == Result::QueryReplay, "latest query replay acknowledged");
  require(f.replies.last.remaining_ms == 1U, "replay reports fresh remaining budget");
  f.dispatcher.tick(600U);
  require(f.dispatcher.snapshot(600U).state == State::Fault, "replay never extends lease");
  report("lost-ack-query-replay-no-renewal", before);
}
void operation_timeout() {
  const unsigned before = checks;
  Fixture f;
  f.start();
  f.deliver(frame(kExecute, 2U), 0U);
  uint32_t sequence = 3U;
  for (uint32_t time = 100U; time < kOperationLimitMs; time += 100U) {
    f.deliver(frame(kKeepalive, sequence++, 0U), time);
  }
  f.dispatcher.tick(kOperationLimitMs - 1U);
  require(f.dispatcher.snapshot(kOperationLimitMs - 1U).busy, "operation busy before deadline");
  f.dispatcher.tick(kOperationLimitMs);
  require(f.dispatcher.snapshot(kOperationLimitMs).state == State::Fault, "operation deadline independent of healthy link");
  require(f.dispatcher.snapshot(kOperationLimitMs).fault == 2U, "operation timeout reason");
  report("operation-timeout-with-healthy-network", before);
}
void command_boundaries() {
  const unsigned before = checks;
  for (uint8_t action = 0U; action < 8U; ++action) {
    Fixture f;
    f.start();
    f.deliver(frame(kExecute, 2U, action), 1U);
    require(f.motion.executions == 1U, "one allowed action callback");
    for (uint32_t sequence : {2U, 4U}) {
      f.deliver(frame(kExecute, sequence, action), 2U);
      require(f.replies.last.result == Result::BadSequence, "busy mutation fails sequence boundary");
      require(f.dispatcher.snapshot(2U).sequence == 2U, "busy rejection preserves accepted sequence");
    }
    f.dispatcher.operation_done();
    for (uint32_t sequence : {2U, 4U}) {
      f.deliver(frame(kExecute, sequence, action), 3U);
      require(f.replies.last.result == Result::BadSequence, "idle mutation fails sequence boundary");
      require(f.dispatcher.snapshot(3U).sequence == 2U, "idle rejection preserves accepted sequence");
    }
    require(f.motion.executions == 1U, "duplicate or reordered mutation never executes twice");
    f.deliver(frame(kExecute, 3U, action), 4U);
    require(f.motion.executions == 2U, "valid next mutation remains usable after rejection");
  }
  Command invalid{kExecute, 2U, 8U, {}};
  Frame encoded{};
  require(!encode_command(invalid, encoded), "invalid action cannot encode");
  invalid.action = 0U;
  invalid.sequence = kMaxSequence + 1U;
  require(!encode_command(invalid, encoded), "oversized sequence cannot encode");
  Fixture f;
  f.start();
  Frame corrupted = frame(kKeepalive, 2U);
  corrupted.bytes[corrupted.size - 3U] ^= 1U;
  f.deliver(corrupted, 50U);
  require(f.dispatcher.snapshot(50U).state == State::Fault, "bad CRC while active faults");
  report("command-allowlist-sequence-and-crc", before);
}
void recovery_boundaries() {
  const unsigned before = checks;
  Fixture normal;
  normal.start();
  normal.deliver(frame(kExecute, 2U), 1U);
  normal.dispatcher.operation_done();
  normal.deliver(frame(kDisarm, 3U), 2U);
  require(normal.dispatcher.snapshot(2U).state == State::Disarmed, "completed action disarms");
  require(normal.motion.disarms == 1U, "normal disarm callback occurs");
  normal.deliver(frame(kBegin, 4U), 3U);
  require(normal.dispatcher.snapshot(3U).state == State::Disarmed, "old session cannot reopen");
  normal.deliver(frame(kBegin, 4U, 0U, 2U), 4U);
  require(normal.dispatcher.snapshot(4U).state == State::Session, "new session and next sequence can recover normal completion");
  require(normal.motion.executions == 1U, "recovery never auto-executes");
  Fixture fault;
  fault.start();
  fault.dispatcher.external_fault(10U);
  require_terminal(fault, 10U, 1U, 3U, 0U);
  fault.deliver(frame(kDisarm, 2U), 11U);
  require(fault.replies.last.result == Result::WrongState, "DISARM cannot clear transport fault");
  require_terminal(fault, 11U, 1U, 3U, 0U);
  // DISARM was rejected: last accepted is still 1, so BEGIN must try 2.
  fault.deliver(frame(kBegin, 2U, 0U, 2U), 12U);
  require(fault.replies.last.result == Result::WrongState, "exact-next fresh-session BEGIN cannot clear fault");
  require_terminal(fault, 12U, 1U, 3U, 0U);
  fault.dispatcher.operation_done();
  fault.dispatcher.tick(1000U);
  require_terminal(fault, 1000U, 1U, 3U, 0U);
  Fixture fresh;  // A new in-memory process, never a hardware reset.
  require(fresh.dispatcher.snapshot(0U).state == State::Boot, "new fixture starts booted");
  require(fresh.motion.executions == 0U, "new fixture never resumes prior work");
  report("normal-recovery-versus-terminal-fault", before);
}
}
int main() {
  stop_and_cancellation();
  latency_and_loss();
  query_replay();
  operation_timeout();
  command_boundaries();
  recovery_boundaries();
  std::printf("simulation-lab: 6 scenario groups, %u checks passed\n", checks);
}
