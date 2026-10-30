"""Synthetic pixels only; never invoke desktop ImageGrab or read image files."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from PIL import Image

import screen

from screen import _encode_jpeg  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


@pytest.fixture
def enable_synthetic_grab(
    monkeypatch: pytest.MonkeyPatch, forbid_real_desktop_capture: None
) -> Callable[[Image.Image], None]:
    # Explicit dependency installs the capture-denial guard before this opt-in.
    _ = forbid_real_desktop_capture

    def enable(source: Image.Image) -> None:
        def grab(*, xdisplay: str) -> Image.Image:
            assert xdisplay == ":20"
            return source

        monkeypatch.setattr("screen.ImageGrab.grab", grab)

    return enable


@pytest.mark.parametrize(
    ("mode", "size", "color", "expected_size", "expected_pixel"),
    [
        ("RGB", (800, 1600), (40, 80, 120), (400, 800), (40, 80, 120)),
        ("RGBA", (2560, 1600), (40, 80, 120, 0), (1280, 800), (40, 80, 120)),
        ("L", (64, 32), 128, (64, 32), (128, 128, 128)),
    ],
)
def test_synthetic_conversion_thumbnail_and_jpeg(
    mode: str,
    size: tuple[int, int],
    color: int | tuple[int, ...],
    expected_size: tuple[int, int],
    expected_pixel: tuple[int, int, int],
    enable_synthetic_grab: Callable[[Image.Image], None],
) -> None:
    with Image.new(mode, size, color) as source:
        original_pixels = source.tobytes()
        enable_synthetic_grab(source)
        frame = screen.capture_frame({"DISPLAY": ":20", "XAUTHORITY": "synthetic-unused-authority"})
        encoded = frame.data
        assert (frame.width, frame.height) == expected_size
        assert source.size == size
        assert source.mode == mode
        assert source.tobytes() == original_pixels
    assert 0 < len(encoded) <= screen.SCREEN_MAX_BYTES
    with Image.open(BytesIO(encoded), formats=["JPEG"]) as decoded:
        decoded.load()
        assert decoded.format == "JPEG"
        assert decoded.mode == "RGB"
        assert decoded.size == expected_size
        pixel = decoded.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        assert all(abs(actual - expected) <= 2 for actual, expected in zip(pixel, expected_pixel, strict=True))


@pytest.fixture
def noisy_image() -> Iterator[Image.Image]:
    pixels = hashlib.shake_256(b"synthetic Pillow compatibility pixels").digest(128 * 128 * 3)
    with Image.frombytes("RGB", (128, 128), pixels) as image:
        yield image


def jpeg_at_quality(image: Image.Image, quality: int) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True)
    return output.getvalue()


def test_jpeg_accepts_exact_byte_limit(noisy_image: Image.Image, monkeypatch: pytest.MonkeyPatch) -> None:
    first = jpeg_at_quality(noisy_image, 82)
    monkeypatch.setattr(screen, "SCREEN_MAX_BYTES", len(first))
    assert _encode_jpeg(noisy_image) == first


def test_jpeg_reduces_quality_to_meet_byte_limit(noisy_image: Image.Image, monkeypatch: pytest.MonkeyPatch) -> None:
    first = jpeg_at_quality(noisy_image, 82)
    smaller = jpeg_at_quality(noisy_image, 70)
    assert len(smaller) < len(first)
    monkeypatch.setattr(screen, "SCREEN_MAX_BYTES", len(smaller))
    encoded = _encode_jpeg(noisy_image)
    assert encoded == smaller
    with Image.open(BytesIO(encoded), formats=["JPEG"]) as decoded:
        decoded.load()
        assert decoded.size == noisy_image.size


def test_jpeg_rejects_when_all_qualities_exceed_limit(
    noisy_image: Image.Image, monkeypatch: pytest.MonkeyPatch
) -> None:
    smallest = min(len(jpeg_at_quality(noisy_image, quality)) for quality in (82, 70, 55, 40))
    monkeypatch.setattr(screen, "SCREEN_MAX_BYTES", smallest - 1)
    with pytest.raises(screen.CaptureError, match="exceeds size limit"):
        _encode_jpeg(noisy_image)
