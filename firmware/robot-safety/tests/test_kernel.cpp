#include "test_support.h"

using robot_safety::CommandResult;
using robot_safety::Opcode;
using robot_safety::State;

int run_kernel_tests(TestContext& test) {
  const int checks_before = test.checks;
  RecordingSafeSink sink;
  robot_safety::SafetyKernel kernel(sink);
  test.require(kernel.snapshot(0).state == State::StopLatched, "boot is latched");
  test.require(sink.safe_calls == 1, "boot forces safe once");

  test.require(kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0) ==
                   CommandResult::Accepted,
               "clear accepts current epoch");
  test.require(kernel.snapshot(0).state == State::Disarmed, "clear disarms protocol");
  test.require(kernel.snapshot(0).epoch == 1, "clear advances epoch");

  test.require(kernel.apply(command(Opcode::Lease, 1, 0, 49), 0) ==
                   CommandResult::TtlRejected,
               "short lease rejected");
  test.require(kernel.apply(command(Opcode::Lease, 1, 0, 100), 0) ==
                   CommandResult::Accepted,
               "lease acquisition accepted");
  test.require(kernel.snapshot(49).state == State::Leased, "lease remains before expiry");
  kernel.tick(100);
  test.require(kernel.snapshot(100).state == State::Disarmed, "lease expires exactly");
  test.require(kernel.snapshot(100).epoch == 2, "expiry advances epoch");
  test.require(sink.safe_calls == 2, "expiry forces safe");

  test.require(kernel.apply(command(Opcode::Lease, 2, 0, 100), 100) ==
                   CommandResult::Accepted,
               "second acquisition accepted");
  test.require(kernel.apply(command(Opcode::Lease, 2, 0, 100), 119) ==
                   CommandResult::SequenceRejected,
               "duplicate lease rejected");
  test.require(kernel.apply(command(Opcode::Lease, 2, 1, 100), 119) ==
                   CommandResult::RateRejected,
               "renewal rate limited");
  test.require(kernel.apply(command(Opcode::Lease, 2, 1, 100), 120) ==
                   CommandResult::Accepted,
               "renewal accepted at rate boundary");
  test.require(kernel.apply(command(Opcode::Lease, 2, 0, 100), 140) ==
                   CommandResult::SequenceRejected,
               "stale sequence rejected");

  const std::uint32_t epoch_before_stop = kernel.snapshot(140).epoch;
  test.require(kernel.apply(command(Opcode::Stop, 0xabcdef01U, 32768), 140) ==
                   CommandResult::Accepted,
               "stop ignores epoch and sequence");
  test.require(kernel.snapshot(140).state == State::StopLatched, "stop latches");
  test.require(kernel.snapshot(140).epoch == epoch_before_stop + 1U,
               "stop advances epoch once");
  test.require(kernel.apply(emergency_stop(), 141) == CommandResult::Accepted,
               "emergency stop accepts zero-version form");
  test.require(kernel.snapshot(141).epoch == epoch_before_stop + 1U,
               "duplicate stop does not advance epoch");

  test.require(kernel.apply(command(Opcode::ClearStopLatch, epoch_before_stop, 0), 150) ==
                   CommandResult::EpochRejected,
               "stale clear rejected");
  test.require(kernel.apply(command(Opcode::ClearStopLatch, epoch_before_stop + 1U, 0), 150) ==
                   CommandResult::Accepted,
               "current clear accepted");
  const std::uint32_t disarmed_epoch = kernel.snapshot(150).epoch;
  test.require(kernel.apply(command(Opcode::Stop, 0, 0), 151) == CommandResult::Accepted,
               "stop from disarmed accepted");
  test.require(kernel.snapshot(151).epoch == disarmed_epoch + 1U,
               "disarmed stop advances epoch");
  test.require(kernel.apply(command(Opcode::Stop, 0, 0), 152) == CommandResult::Accepted,
               "repeated stop from latched accepted");
  test.require(kernel.snapshot(152).epoch == disarmed_epoch + 1U,
               "latched stop remains idempotent");

  RecordingSafeSink rejected_sink;
  robot_safety::SafetyKernel rejected_kernel(rejected_sink);
  rejected_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0);
  rejected_kernel.apply(command(Opcode::Lease, 1, 0, 100), 0);
  test.require(rejected_kernel.apply(command(Opcode::Lease, 1, 1, 100), 10) ==
                   CommandResult::RateRejected,
               "rate rejection does not renew lease");
  test.require(rejected_kernel.apply(command(Opcode::Lease, 1, 0, 100), 20) ==
                   CommandResult::SequenceRejected,
               "stale rejection does not renew lease");
  rejected_kernel.tick(100);
  test.require(rejected_kernel.snapshot(100).state == State::Disarmed,
               "rate and stale rejection leave original deadline intact");

  RecordingSafeSink wrap_sink;
  robot_safety::SafetyKernel wrap_kernel(wrap_sink);
  test.require(wrap_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0) ==
                   CommandResult::Accepted,
               "wrap test clear accepted");
  test.require(wrap_kernel.apply(command(Opcode::Lease, 1, 0, 50), 0xfffffff0U) ==
                   CommandResult::Accepted,
               "wrap test lease accepted");
  wrap_kernel.tick(0x0000001dU);
  test.require(wrap_kernel.snapshot(0x0000001dU).state == State::Leased,
               "millis wrap remains leased before deadline");
  wrap_kernel.tick(0x00000022U);
  test.require(wrap_kernel.snapshot(0x00000022U).state == State::Disarmed,
               "millis wrap expires at deadline");

  RecordingSafeSink sequence_sink;
  robot_safety::SafetyKernel sequence_kernel(sequence_sink);
  sequence_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0);
  sequence_kernel.apply(command(Opcode::Lease, 1, 0, 100), 0);
  test.require(sequence_kernel.apply(command(Opcode::Lease, 1, 32767, 100), 20) ==
                   CommandResult::Accepted,
               "maximum forward sequence delta accepted");

  RecordingSafeSink half_range_sink;
  robot_safety::SafetyKernel half_range_kernel(half_range_sink);
  half_range_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0);
  half_range_kernel.apply(command(Opcode::Lease, 1, 0, 100), 0);
  test.require(half_range_kernel.apply(command(Opcode::Lease, 1, 32768, 100), 20) ==
                   CommandResult::SequenceRejected,
               "half-range sequence delta rejected");

  RecordingSafeSink bounds_sink;
  robot_safety::SafetyKernel bounds_kernel(bounds_sink);
  test.require(bounds_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0) ==
                   CommandResult::Accepted,
               "bounds clear accepted");
  test.require(bounds_kernel.apply(command(Opcode::Lease, 1, 0, 50), 0) ==
                   CommandResult::Accepted,
               "minimum ttl accepted");
  bounds_kernel.tick(50);
  test.require(bounds_kernel.apply(command(Opcode::Lease, 2, 0, 500), 50) ==
                   CommandResult::Accepted,
               "maximum ttl accepted");
  test.require(bounds_kernel.apply(command(Opcode::Lease, 2, 1, 501), 70) ==
                   CommandResult::TtlRejected,
               "ttl above maximum rejected");

  RecordingSafeSink sequence_wrap_sink;
  robot_safety::SafetyKernel sequence_wrap_kernel(sequence_wrap_sink);
  sequence_wrap_kernel.apply(command(Opcode::ClearStopLatch, 0, 0), 0);
  sequence_wrap_kernel.apply(command(Opcode::Lease, 1, 0, 500), 0);
  test.require(sequence_wrap_kernel.apply(command(Opcode::Lease, 1, 32767, 500), 20) ==
                   CommandResult::Accepted,
               "first half-range jump accepted");
  test.require(sequence_wrap_kernel.apply(command(Opcode::Lease, 1, 65534, 500), 40) ==
                   CommandResult::Accepted,
               "second half-range jump accepted");
  test.require(sequence_wrap_kernel.apply(command(Opcode::Lease, 1, 65535, 500), 60) ==
                   CommandResult::Accepted,
               "sequence reaches maximum");
  test.require(sequence_wrap_kernel.apply(command(Opcode::Lease, 1, 0, 500), 80) ==
                   CommandResult::Accepted,
               "sequence wraps to zero");

  return test.checks - checks_before;
}
