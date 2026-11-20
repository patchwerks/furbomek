"""Offline candidate consistency checks, explicitly without an installed trust root."""

import hashlib
from dataclasses import dataclass
from typing import Final

from models import EvidenceKind, Manifest

RELEASE_HOLDS: Final = (
    "trusted_installed_authenticated_link_unavailable",
    "instrumented_independent_cutoff_unverified",
    "instrumented_stage_and_containment_unverified",
    "current_operator_authorization_unverified",
    "matched_integrated_live_scope_unverified",
    "representative_private_24h_soak_unverified",
    "live_execution_not_implemented_in_offline_gate",
)


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    checked_envelopes: int
    holds: tuple[str, ...]
    trust: str = "untrusted_candidate_envelopes"


def check_evidence(data: Manifest, now_unix_ms: int) -> EvidenceResult:
    holds: list[str] = []
    kinds = [item.kind for item in data.evidence]
    for kind in EvidenceKind:
        if kind not in kinds:
            holds.append(f"missing_evidence:{kind.value}")
    if len(set(kinds)) != len(kinds):
        holds.append("duplicate_evidence_kind")
    for item in data.evidence:
        if hashlib.sha256(item.payload.encode()).hexdigest() != item.payload_sha256:
            holds.append(f"wrong_digest:{item.kind.value}")
        if item.scope != data.scope:
            holds.append(f"scope_mismatch:{item.kind.value}")
        if not item.captured_unix_ms <= now_unix_ms < item.expires_unix_ms:
            holds.append(f"stale_or_future_evidence:{item.kind.value}")
        if item.expires_unix_ms - item.captured_unix_ms > 86_400_000:
            holds.append(f"excessive_validity:{item.kind.value}")
    return EvidenceResult(len(data.evidence), tuple(holds))
