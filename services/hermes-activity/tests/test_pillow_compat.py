"""Synthetic pixels only; never invoke capture or read external image files."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import TYPE_CHECKING

import pytest
from PIL import Image

import screen

# Exercise the pure encoder without entering the unqualified capture entrypoint.
from screen import _encode_jpeg  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    from collections.abc import Iterator


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
) -> None:
    # Match the helper's image operations without invoking ImageGrab/capture_frame.
    with Image.new(mode, size, color) as source, source.convert("RGB") as image:
        image.thumbnail(screen.SCREEN_SIZE)
        encoded = _encode_jpeg(image)
        assert source.size == size
        assert image.size == expected_size
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
