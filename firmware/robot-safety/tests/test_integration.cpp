#include "test_support.h"

int run_integration_tests(TestContext& test) {
  const int checks_before = test.checks;
  EventLog events;
  RecordingSafeSink safe_sink(&events);
  RecordingReplySink reply_sink(&events);
  TestCommitFaultSignal engine_signal;
  robot_safety::ProtocolEngine engine(safe_sink, reply_sink, engine_signal);
  test.require(engine.snapshot(0).state == robot_safety::State::StopLatched,
               "protocol boots stopped");

  feed(engine, encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)), 0);
  feed(engine, encode(command(robot_safety::Opcode::Lease, 1, 0, 100)), 0);
  test.require(engine.snapshot(0).state == robot_safety::State::Leased,
               "parser and kernel acquire lease");
  test.require(reply_sink.frames.size() == 2U, "accepted commands reply");
  test.require(body_has_result(reply_sink.frames[1], robot_safety::CommandResult::Accepted),
               "lease response says accepted");

  const std::size_t event_count = events.events.size();
  feed(engine, encode(command(robot_safety::Opcode::Stop, 999, 32768)), 1);
  test.require(engine.snapshot(1).state == robot_safety::State::StopLatched,
               "stop has priority over stale fields");
  test.require(events.events.size() == event_count + 2U, "stop and reply are recorded");
  test.require(events.events[event_count] == 1 && events.events[event_count + 1U] == 2,
               "safe sink runs before reply queue");
  const std::uint32_t stopped_epoch = engine.snapshot(1).epoch;
  feed(engine, encode(emergency_stop()), 2);
  test.require(engine.snapshot(2).epoch == stopped_epoch, "duplicate emergency stop idempotent");

  feed(engine, encode(command(robot_safety::Opcode::ClearStopLatch, stopped_epoch - 1U, 0)), 3);
  test.require(engine.snapshot(3).state == robot_safety::State::StopLatched,
               "stale clear cannot unlatch");

  EventLog malformed_events;
  RecordingSafeSink malformed_safe(&malformed_events);
  RecordingReplySink malformed_replies(&malformed_events);
  TestCommitFaultSignal malformed_signal;
  robot_safety::ProtocolEngine malformed_engine(malformed_safe, malformed_replies, malformed_signal);
  feed(malformed_engine, encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)), 0);
  feed(malformed_engine, encode(command(robot_safety::Opcode::Lease, 1, 0, 100)), 0);
  auto malformed = encode(command(robot_safety::Opcode::Status, 1, 0));
  malformed.bytes[malformed.size - 1U] ^= 0x01U;
  feed(malformed_engine, malformed, 50);
  test.require(malformed_engine.snapshot(50).state == robot_safety::State::Leased,
               "bad crc does not alter lease");
  malformed_engine.tick(100);
  test.require(malformed_engine.snapshot(100).state == robot_safety::State::Disarmed,
               "malformed input does not extend lease");

  EventLog fault_events;
  RecordingSafeSink fault_safe(&fault_events);
  RecordingReplySink fault_replies(&fault_events);
  TestCommitFaultSignal fault_signal;
  robot_safety::ProtocolEngine fault_engine(fault_safe, fault_replies, fault_signal);
  feed(fault_engine, encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)), 0);
  feed(fault_engine, encode(command(robot_safety::Opcode::Lease, 1, 0, 100)), 0);
  fault_engine.transport_fault(10);
  test.require(fault_engine.sticky_transport_fault(), "transport fault is sticky");
  test.require(fault_engine.snapshot(10).state == robot_safety::State::StopLatched,
               "transport fault stops");
  const std::size_t fault_reply_count = fault_replies.frames.size();
  feed(fault_engine, encode(command(robot_safety::Opcode::ClearStopLatch, 2, 0)), 11);
  test.require(fault_engine.snapshot(11).state == robot_safety::State::StopLatched,
               "sticky fault blocks clear");
  test.require(fault_replies.frames.size() == fault_reply_count,
               "sticky fault drops buffered commands");

  EventLog deadline_events;
  RecordingSafeSink deadline_safe(&deadline_events);
  RecordingReplySink deadline_replies(&deadline_events);
  TestCommitFaultSignal deadline_signal;
  robot_safety::ProtocolEngine deadline_engine(deadline_safe, deadline_replies, deadline_signal);
  feed(deadline_engine, encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)), 0);
  feed(deadline_engine, encode(command(robot_safety::Opcode::Lease, 1, 0, 50)), 0);
  const std::size_t deadline_replies_before = deadline_replies.frames.size();
  const auto deadline_renewal = encode(command(robot_safety::Opcode::Lease, 1, 1, 100));
  for (std::uint8_t index = 0; index < deadline_renewal.size; ++index) {
    const std::uint32_t arrival = index + 1U == deadline_renewal.size ? 50U : 49U;
    deadline_engine.receive(deadline_renewal.bytes[index], arrival);
  }
  deadline_engine.tick(50);
  test.require(deadline_engine.snapshot(50).state == robot_safety::State::Disarmed,
               "deadline renewal cannot revive expired lease");
  test.require(deadline_replies.frames.size() == deadline_replies_before + 1U &&
                   body_has_result(deadline_replies.frames.back(),
                                   robot_safety::CommandResult::EpochRejected),
               "deadline renewal reports epoch rejection after expiry");

  EventLog backpressure_events;
  RecordingSafeSink backpressure_safe(&backpressure_events);
  RecordingReplySink backpressure_replies(&backpressure_events);
  TestCommitFaultSignal backpressure_signal;
  robot_safety::ProtocolEngine backpressure_engine(backpressure_safe,
                                                   backpressure_replies,
                                                   backpressure_signal);
  feed(backpressure_engine, encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)), 0);
  backpressure_replies.available = false;
  const int safe_calls_before_stop = backpressure_safe.safe_calls;
  feed(backpressure_engine, encode(command(robot_safety::Opcode::Stop, 0, 99)), 1);
  test.require(backpressure_engine.snapshot(1).state == robot_safety::State::StopLatched,
               "stop works while telemetry is backpressured");
  test.require(backpressure_safe.safe_calls == safe_calls_before_stop + 1,
               "backpressure stop still forces safe");

  EventLog before_commit_events;
  RecordingSafeSink before_commit_safe(&before_commit_events);
  RecordingReplySink before_commit_replies(&before_commit_events);
  TestCommitFaultSignal before_commit_signal;
  before_commit_signal.inject_before = true;
  robot_safety::ProtocolEngine before_commit_engine(before_commit_safe,
                                                    before_commit_replies,
                                                    before_commit_signal);
  feed(before_commit_engine,
       encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)),
       0);
  test.require(before_commit_engine.sticky_transport_fault() &&
                   before_commit_engine.snapshot(0).state == robot_safety::State::StopLatched,
               "fault before commit latches transport stop");
  test.require(before_commit_replies.frames.size() == 1U &&
                   body_has_result(before_commit_replies.frames.front(),
                                   robot_safety::CommandResult::TransportFault),
               "fault before commit cannot report accepted reply");
  test.require(before_commit_signal.in_commit == false &&
                   before_commit_signal.enter_count == before_commit_signal.leave_count,
               "commit boundary restores native state");

  EventLog after_commit_events;
  RecordingSafeSink after_commit_safe(&after_commit_events);
  RecordingReplySink after_commit_replies(&after_commit_events);
  TestCommitFaultSignal after_commit_signal;
  after_commit_signal.inject_after = true;
  robot_safety::ProtocolEngine after_commit_engine(after_commit_safe,
                                                   after_commit_replies,
                                                   after_commit_signal);
  feed(after_commit_engine,
       encode(command(robot_safety::Opcode::ClearStopLatch, 0, 0)),
       0);
  test.require(after_commit_replies.frames.size() == 1U &&
                   body_has_result(after_commit_replies.frames.front(),
                                   robot_safety::CommandResult::Accepted),
               "fault after commit preserves accepted reply");
  test.require(after_commit_engine.sticky_transport_fault() &&
                   after_commit_engine.snapshot(0).state == robot_safety::State::StopLatched,
               "fault after commit latches after accepted command");
  const std::size_t after_commit_reply_count = after_commit_replies.frames.size();
  feed(after_commit_engine,
       encode(command(robot_safety::Opcode::ClearStopLatch, 1, 0)),
       1);
  test.require(after_commit_replies.frames.size() == after_commit_reply_count,
               "latched post-commit fault blocks clear");

  return test.checks - checks_before;
}
