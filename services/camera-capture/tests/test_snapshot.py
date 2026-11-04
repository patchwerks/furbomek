# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#   "pytest==8.4.2", "numpy==1.26.4",
#   "opencv-contrib-python-headless==4.11.0.86", "pydantic==2.12.3",
# ]
# ///
"""Exercise the tracker revalidation seam without camera or model startup."""

import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vision_frames import frame_sequence_matches


def test_missing_ring_slot_is_not_current(tmp_path: Path) -> None:
    assert not frame_sequence_matches(tmp_path / "frame-1.bin", 5)


def test_matching_header_is_current(tmp_path: Path) -> None:
    path = tmp_path / "frame-1.bin"
    path.write_bytes(struct.pack("<4I", 0x32434B46, 1, 5, 217088))
    assert frame_sequence_matches(path, 5)


def test_reused_or_partial_slot_is_not_current(tmp_path: Path) -> None:
    path = tmp_path / "frame-1.bin"
    path.write_bytes(struct.pack("<4I", 0x32434B46, 1, 6, 217088))
    assert not frame_sequence_matches(path, 5)
    path.write_bytes(b"short")
    assert not frame_sequence_matches(path, 5)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
