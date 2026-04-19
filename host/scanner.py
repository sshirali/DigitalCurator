"""Scanner: traverses a directory and indexes all image files."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Callable, Optional

import imagehash
from PIL import Image, ExifTags  # noqa: F401 – ExifTags kept for clarity

from host.duplicate_detector import DuplicateDetector
from host.indexer import Indexer
from host.models import (
    FileRecord,
    ImageMetadata,
    QualityConfig,
    ScanResult,
)
from host.quality_assessor import QualityAssessor
from host.screenshot_detector import ScreenshotDetector
from host.thumbnail_generator import ThumbnailGenerator

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}

# EXIF tag IDs for capture date
_TAG_DATETIME_ORIGINAL = 0x9003
_TAG_DATETIME = 0x0132


def _sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file, reading in 64 KiB chunks."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_metadata(path: Path) -> ImageMetadata:
    """Open image with Pillow and extract dimension + EXIF info."""
    with Image.open(path) as img:
        width, height = img.size
        exif_data = img.getexif()
        has_exif = len(exif_data) > 0
        has_capture_date = (
            _TAG_DATETIME_ORIGINAL in exif_data
            or _TAG_DATETIME in exif_data
        )
    return ImageMetadata(
        width=width,
        height=height,
        has_exif=has_exif,
        has_capture_date=has_capture_date,
        filename=path.name,
    )


class Scanner:
    """Scans a directory tree, indexes image files, and detects duplicates."""

    def __init__(
        self,
        indexer: Optional[Indexer] = None,
        screenshot_detector: Optional[ScreenshotDetector] = None,
        quality_assessor: Optional[QualityAssessor] = None,
        thumbnail_generator: Optional[ThumbnailGenerator] = None,
        duplicate_detector: Optional[DuplicateDetector] = None,
    ) -> None:
        self._indexer = indexer or Indexer()
        self._screenshot_detector = (
            screenshot_detector or ScreenshotDetector()
        )
        self._quality_assessor = quality_assessor or QualityAssessor()
        self._thumbnail_generator = (
            thumbnail_generator or ThumbnailGenerator()
        )
        self._duplicate_detector = (
            duplicate_detector or DuplicateDetector()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        directory: Path,
        progress_callback: Callable[[float], None],
    ) -> ScanResult:
        """Scan *directory* recursively and index all supported image files.

        Args:
            directory: Root directory to scan.
            progress_callback: Called with a float in [0, 100] after each
                file is processed.

        Returns:
            ScanResult summarising totals and detected duplicate groups.
        """
        image_files = [
            p
            for p in directory.rglob("*")
            if p.is_file()
            and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        total = len(image_files)
        indexed = 0
        failed = 0
        all_records: list[FileRecord] = []

        for i, path in enumerate(image_files):
            record = self._process_file(path)
            if record is None:
                failed += 1
            else:
                all_records.append(record)
                indexed += 1

            files_processed = i + 1
            progress = files_processed / total * 100.0 if total > 0 else 100.0
            progress_callback(progress)

        # Duplicate detection across all successfully indexed records
        duplicate_groups = self._duplicate_detector.detect(all_records)
        for group in duplicate_groups:
            self._indexer.upsert_group(group)

        return ScanResult(
            total_files=total,
            indexed_files=indexed,
            failed_files=failed,
            duplicate_groups=duplicate_groups,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _process_file(self, path: Path) -> FileRecord | None:
        """Process a single image file and upsert it into the index.

        Returns the FileRecord on success, or None if the file could not
        be processed.
        """
        try:
            stat = path.stat()
            sha = _sha256(path)
            phash_val = str(imagehash.phash(Image.open(path)))
            metadata = _extract_metadata(path)

            quality_config = QualityConfig()
            quality_result = self._quality_assessor.assess(
                path, quality_config
            )
            screenshot_result = self._screenshot_detector.classify(
                path, metadata
            )

            record = FileRecord(
                id=None,
                abs_path=path.resolve(),
                file_size=stat.st_size,
                last_modified=stat.st_mtime,
                sha256=sha,
                phash=phash_val,
                thumb_path=None,
                thumb_status="pending",
                is_screenshot=screenshot_result.is_candidate,
                screenshot_conf=screenshot_result.confidence,
                laplacian_var=quality_result.laplacian_variance,
                mean_luminance=quality_result.mean_luminance,
                is_blurry=quality_result.is_blurry,
                is_dark=quality_result.is_dark,
                decision="undecided",
                status="active",
            )

            thumb_path = self._thumbnail_generator.get_or_create(record)
            if thumb_path is not None:
                record.thumb_path = thumb_path
                record.thumb_status = "ok"
            else:
                record.thumb_status = "unavailable"

            self._indexer.upsert_file(record)
            return record

        except Exception as exc:
            logger.warning("Skipping unreadable file %s: %s", path, exc)
            return None
