"""Actual descriptor races preserve private mailbox trust and bounded reads."""

import os
from pathlib import Path

import pytest

from furbomek_gateway.production_mailbox import PrivateMailbox, ReceiptReplacedError
from furbomek_gateway.reaction_types import StorePrivacyError


def test_reopens_receipt_replaced_between_open_and_fstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "old")
        replacement = tmp_path / "replacement"
        _ = replacement.write_text("current")
        replacement.chmod(0o600)
        original_fstat = os.fstat
        links: list[int] = []

        def replace_before_fstat(descriptor: int) -> os.stat_result:
            if not links:
                _ = replacement.replace(tmp_path / "effects-ack.json")
            result = original_fstat(descriptor)
            links.append(result.st_nlink)
            return result

        monkeypatch.setattr(os, "fstat", replace_before_fstat)
        assert mailbox.read("effects-ack.json") == b"current"
        assert links[0] == 0


def test_hardlinked_receipt_remains_a_privacy_failure(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "private")
        os.link(tmp_path / "effects-ack.json", tmp_path / "alias")
        with pytest.raises(StorePrivacyError):
            _ = mailbox.read("effects-ack.json")


def test_repeated_replacement_is_typed_unavailable_after_one_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "old")
        original_fstat = os.fstat
        links: list[int] = []

        def replace_every_open(descriptor: int) -> os.stat_result:
            replacement = tmp_path / "replacement"
            _ = replacement.write_text("unstable")
            replacement.chmod(0o600)
            _ = replacement.replace(tmp_path / "effects-ack.json")
            result = original_fstat(descriptor)
            links.append(result.st_nlink)
            return result

        monkeypatch.setattr(os, "fstat", replace_every_open)
        with pytest.raises(ReceiptReplacedError):
            _ = mailbox.read("effects-ack.json")
        assert links == [0, 0]


def test_replacement_after_read_discards_obsolete_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "old")
        replacement = tmp_path / "replacement"
        _ = replacement.write_text("current")
        replacement.chmod(0o600)
        original_fstat = os.fstat
        links: list[int] = []

        def replace_at_second_check(descriptor: int) -> os.stat_result:
            if len(links) == 1:
                _ = replacement.replace(tmp_path / "effects-ack.json")
            result = original_fstat(descriptor)
            links.append(result.st_nlink)
            return result

        monkeypatch.setattr(os, "fstat", replace_at_second_check)
        assert mailbox.read("effects-ack.json") == b"current"
        assert links[:2] == [1, 0]


@pytest.mark.parametrize("mode", [0o644, 0o666])
def test_replaced_wrong_mode_remains_privacy_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: int,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "old")
        receipt = tmp_path / "effects-ack.json"
        receipt.chmod(mode)
        replacement = tmp_path / "replacement"
        _ = replacement.write_text("current")
        replacement.chmod(0o600)
        original_fstat = os.fstat

        def replace_insecure_receipt(descriptor: int) -> os.stat_result:
            _ = replacement.replace(receipt)
            return original_fstat(descriptor)

        monkeypatch.setattr(os, "fstat", replace_insecure_receipt)
        with pytest.raises(StorePrivacyError):
            _ = mailbox.read("effects-ack.json")


def test_reopen_cannot_follow_replacement_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "old")
        replacement = tmp_path / "replacement"
        replacement.symlink_to(tmp_path / "production-media.lock")
        original_fstat = os.fstat

        def replace_with_symlink(descriptor: int) -> os.stat_result:
            _ = replacement.replace(tmp_path / "effects-ack.json")
            return original_fstat(descriptor)

        monkeypatch.setattr(os, "fstat", replace_with_symlink)
        with pytest.raises(OSError, match=r"Too many levels|symbolic links"):
            _ = mailbox.read("effects-ack.json")


def test_wrong_owner_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        mailbox.write("effects-ack.json", "private")
        wrong_uid = os.getuid() + 1
        monkeypatch.setattr(os, "getuid", lambda: wrong_uid)
        with pytest.raises(StorePrivacyError):
            _ = mailbox.read("effects-ack.json")


def test_oversized_receipt_remains_rejected(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    with PrivateMailbox(tmp_path) as mailbox:
        receipt = tmp_path / "effects-ack.json"
        _ = receipt.write_bytes(b"x" * 8193)
        receipt.chmod(0o600)
        with pytest.raises(StorePrivacyError):
            _ = mailbox.read("effects-ack.json")
