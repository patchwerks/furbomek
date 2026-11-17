from __future__ import annotations

from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from window_consent import ConsentMode, WindowConsentStore
from window_capture import WindowIdentity


def identity(*, xid: int = 42, pid: int = 100) -> WindowIdentity:
    return WindowIdentity(
        window_id=xid,
        pid=pid,
        uid=1000,
        process_start_time=12.5,
        display=":20",
        profile_generation="desktop-generation",
        width=800,
        height=600,
        instance="browser",
        class_name="Browser",
    )


def test_share_and_shutter_are_monotonic_and_owner_only(tmp_path: Path) -> None:
    store = WindowConsentStore(tmp_path / "profile", tmp_path / "output")

    first = store.share(identity())
    second = store.shutter()

    assert first.mode is ConsentMode.SHARED
    assert second.mode is ConsentMode.SHUTTERED
    assert second.generation > first.generation
    assert (tmp_path / "output" / "window-consent.json").stat().st_mode & 0o077 == 0


def test_boot_invalidates_previous_share_and_resume_rebinds_identity(tmp_path: Path) -> None:
    store = WindowConsentStore(tmp_path / "profile", tmp_path / "output")
    shared = store.share(identity())
    booted = store.boot()

    assert shared.mode is ConsentMode.SHARED
    assert booted.mode is ConsentMode.SHUTTERED
    assert booted.boot_nonce != shared.boot_nonce
    assert booted.generation > shared.generation

    resumed = store.resume(identity(xid=99, pid=101))
    assert resumed.mode is ConsentMode.SHARED
    assert resumed.window_id == 99
    assert resumed.pid == 101
    assert resumed.generation > booted.generation


def test_resume_requires_existing_target(tmp_path: Path) -> None:
    store = WindowConsentStore(tmp_path / "profile", tmp_path / "output")

    with pytest.raises(ValueError, match="no selected window"):
        store.resume(identity())
