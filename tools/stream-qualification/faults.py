"""Replay a deliberately non-operational admission model, never hardware behavior."""

from dataclasses import dataclass
from typing import assert_never

from models import Action, Fault, FaultCase


@dataclass(frozen=True, slots=True)
class FaultResult:
    fault: str
    dispatches: int
    held_dispatches: int
    stale_resume: bool
    fallback: str
    holds: tuple[str, ...]


def replay(case: FaultCase) -> FaultResult:
    qualified = pending = lost = recovered = False
    dispatches = held = 0
    loss_count = recovery_count = 0
    stale_resume = False
    after_recovery_hold = after_requalification_dispatch = False
    during_loss_hold = stale_trigger_hold = False
    previous = -1
    holds: list[str] = []
    fallback = "fixed_rgb"
    for event in case.events:
        if event.at_ns <= previous:
            holds.append("nonmonotonic_fault_events")
        previous = event.at_ns
        match event.action:
            case Action.QUALIFY:
                if not lost:
                    qualified = True
            case Action.TRIGGER:
                pending = qualified and not lost
            case Action.DISPATCH:
                if pending and qualified and not lost:
                    dispatches += 1
                    after_requalification_dispatch |= recovered
                else:
                    held += 1
                    after_recovery_hold |= recovered and not qualified
                    during_loss_hold |= lost
                    stale_trigger_hold |= recovered and qualified and not pending
                stale_resume |= recovered and pending and not qualified
                pending = False
            case Action.LOSS:
                qualified = pending = False
                lost = True
                loss_count += 1
                if case.fault == Fault.OVERRIDE:
                    fallback = "owner_override"
            case Action.RECOVER:
                if not lost:
                    holds.append("recovery_without_loss")
                lost = False
                recovered = True
                recovery_count += 1
            case unreachable:
                assert_never(unreachable)
    if loss_count != 1 or recovery_count != 1:
        holds.append("fault_lifecycle_incomplete")
    if (
        not during_loss_hold
        or not stale_trigger_hold
        or not after_recovery_hold
        or not after_requalification_dispatch
        or stale_resume
    ):
        holds.append("resume_prerequisites_not_exercised")
    if case.fault == Fault.EARLY and dispatches != 1:
        holds.append("early_loss_dispatched")
    return FaultResult(
        case.fault.value, dispatches, held, stale_resume, fallback, tuple(holds)
    )


def matrix(
    cases: tuple[FaultCase, ...],
) -> tuple[tuple[FaultResult, ...], tuple[str, ...]]:
    faults = [case.fault for case in cases]
    holds = [f"missing_fault:{fault.value}" for fault in Fault if fault not in faults]
    if len(faults) != len(set(faults)):
        holds.append("duplicate_fault")
    results = tuple(replay(case) for case in cases)
    holds.extend(
        f"{result.fault}:{reason}" for result in results for reason in result.holds
    )
    return results, tuple(holds)
