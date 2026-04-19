"""Unit tests for ThumbnailGenerator."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from host.models import FileRecord
from host.thumbnail_generator import ThumbnailGenerator, MAX_DIM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jpeg(path: Path, width: int, height: int, color: str = "red") -> None:
    """Save a plain JPEG image (no EXIF) at the given path."""
    img = Image.new("RGB", (width, height), color=color)
    img.save(path, format="JPEG")


def _make_record(
    abs_path: Path,
    sha256: str = "a" * 64,
    last_modified: float = 1_000_000.0,
) -> FileRecord:
    return FileRecord(
        id=None,
        abs_path=abs_path,
        file_size=1024,
        last_modified=last_modified,
        sha256=sha256,
        phash="0" * 16,
        thumb_path=None,
        thumb_status="pending",
        is_screenshot=False,
        screenshot_conf=0,
        laplacian_var=None,
        mean_luminance=None,
        is_blurry=False,
        is_dark=False,
        decision="undecided",
        status="active",
    )


# ---------------------------------------------------------------------------
# generate() tests
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_generates_jpeg_for_valid_image(self, tmp_path):
        src = tmp_path / "photo.jpg"
        dest = tmp_path / "thumb.jpg"
        _make_jpeg(src, 800, 600)

        gen = ThumbnailGenerator()
        result = gen.generate(src, dest)

        assert result is True
        assert dest.exists()
        with Image.open(dest) as img:
            assert img.format == "JPEG"

    def test_longest_side_capped_at_400(self, tmp_path):
        src = tmp_path / "big.jpg"
        dest = tmp_path / "thumb.jpg"
        _make_jpeg(src, 1600, 900)

        ThumbnailGenerator().generate(src, dest)

        with Image.open(dest) as img:
            assert max(img.size) <= MAX_DIM

    def test_small_image_not_upscaled(self, tmp_path):
        src = tmp_path / "small.jpg"
        dest = tmp_path / "thumb.jpg"
        _make_jpeg(src, 100, 80)

        ThumbnailGenerator().generate(src, dest)

        with Image.open(dest) as img:
            assert img.size == (100, 80)

    def test_portrait_orientation_respected(self, tmp_path):
        src = tmp_path / "portrait.jpg"
        dest = tmp_path / "thumb.jpg"
        _make_jpeg(src, 300, 1200)

        ThumbnailGenerator().generate(src, dest)

        with Image.open(dest) as img:
            w, h = img.size
            assert h <= MAX_DIM
            assert w <= MAX_DIM

    def test_returns_false_for_corrupt_file(self, tmp_path):
        src = tmp_path / "corrupt.jpg"
        dest = tmp_path / "thumb.jpg"
        src.write_bytes(b"not an image")

        result = ThumbnailGenerator().generate(src, dest)

        assert result is False
        assert not dest.exists()

    def test_no_partial_file_left_on_failure(self, tmp_path):
        src = tmp_path / "bad.jpg"
        dest = tmp_path / "thumb.jpg"
        src.write_bytes(b"\xff\xd8\xff")  # truncated JPEG header

        ThumbnailGenerator().generate(src, dest)

        assert not dest.exists()

    def test_strips_exif_metadata(self, tmp_path):
        """Thumbnail must contain no EXIF data."""
        src = tmp_path / "exif.jpg"
        dest = tmp_path / "thumb.jpg"

        # Build a JPEG with minimal EXIF-like APP1 marker manually via Pillow
        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        # Pillow doesn't add EXIF by default; we inject it via exif kwarg
        exif_data = img.getexif()
        exif_data[0x010F] = "TestCamera"  # Make tag
        img.save(buf, format="JPEG", exif=exif_data.tobytes())
        src.write_bytes(buf.getvalue())

        ThumbnailGenerator().generate(src, dest)

        with Image.open(dest) as thumb:
            exif = thumb.getexif()
            assert len(exif) == 0, f"Expected no EXIF, got: {dict(exif)}"

    def test_creates_parent_directories(self, tmp_path):
        src = tmp_path / "photo.jpg"
        dest = tmp_path / "a" / "b" / "c" / "thumb.jpg"
        _make_jpeg(src, 200, 200)

        result = ThumbnailGenerator().generate(src, dest)

        assert result is True
        assert dest.exists()


# ---------------------------------------------------------------------------
# get_or_create() tests
# ---------------------------------------------------------------------------

class TestGetOrCreate:
    def test_returns_path_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host.thumbnail_generator.THUMB_DIR", tmp_path)
        src = tmp_path / "photo.jpg"
        _make_jpeg(src, 400, 300)
        record = _make_record(src)

        result = ThumbnailGenerator().get_or_create(record)

        assert result is not None
        assert result.exists()

    def test_cache_key_uses_first_16_chars_of_sha256(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host.thumbnail_generator.THUMB_DIR", tmp_path)
        sha = "abcdef1234567890" + "x" * 48
        src = tmp_path / "photo.jpg"
        _make_jpeg(src, 200, 200)
        record = _make_record(src, sha256=sha)

        result = ThumbnailGenerator().get_or_create(record)

        assert result is not None
        assert result.name == "abcdef1234567890.jpg"

    def test_reuses_existing_thumbnail_when_mtime_matches(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host.thumbnail_generator.THUMB_DIR", tmp_path)
        src = tmp_path / "photo.jpg"
        _make_jpeg(src, 200, 200)
        record = _make_record(src, last_modified=9999.0)

        gen = ThumbnailGenerator()
        first = gen.get_or_create(record)
        first_mtime = first.stat().st_mtime

        second = gen.get_or_create(record)

        assert second == first
        assert second.stat().st_mtime == first_mtime

    def test_regenerates_when_mtime_differs(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host.thumbnail_generator.THUMB_DIR", tmp_path)
        src = tmp_path / "photo.jpg"
        _make_jpeg(src, 200, 200)

        gen = ThumbnailGenerator()
        record_v1 = _make_record(src, last_modified=1000.0)
        gen.get_or_create(record_v1)

        # Update source and change mtime
        _make_jpeg(src, 300, 300, color="green")
        record_v2 = _make_record(src, last_modified=2000.0)
        result = gen.get_or_create(record_v2)

        assert result is not None

    def test_returns_none_for_corrupt_source(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host.thumbnail_generator.THUMB_DIR", tmp_path)
        src = tmp_path / "corrupt.jpg"
        src.write_bytes(b"garbage")
        record = _make_record(src)

        result = ThumbnailGenerator().get_or_create(record)

        assert result is None
