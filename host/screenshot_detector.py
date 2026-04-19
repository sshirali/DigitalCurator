"""Screenshot detection for Digital Curator MVP."""

from __future__ import annotations

from pathlib import Path

from host.models import ImageMetadata, ScreenshotResult

# Known screen aspect ratios (portrait orientation)
_SCREEN_RATIOS = [9 / 19.5, 9 / 16, 2 / 3]
# Include landscape inverses
_ALL_RATIOS = _SCREEN_RATIOS + [1 / r for r in _SCREEN_RATIOS]
_TOLERANCE = 0.05


class ScreenshotDetector:
    """Stateless per-file classifier that returns a confidence score 0–3."""

    def classify(self, path: Path, metadata: ImageMetadata) -> ScreenshotResult:
        """Classify an image as a screenshot candidate.

        Criteria (each adds 1 to confidence):
        1. No EXIF metadata AND aspect ratio matches a known screen ratio (±0.05)
        2. Filename contains "screenshot" (case-insensitive)
        3. No EXIF capture date

        Returns:
            ScreenshotResult with is_candidate=True when confidence >= 1.
        """
        confidence = 0

        # Criterion 1: no EXIF + matching aspect ratio
        if not metadata.has_exif and self._matches_screen_ratio(metadata.width, metadata.height):
            confidence += 1

        # Criterion 2: filename contains "screenshot"
        if "screenshot" in metadata.filename.lower():
            confidence += 1

        # Criterion 3: no EXIF capture date
        if not metadata.has_capture_date:
            confidence += 1

        return ScreenshotResult(is_candidate=confidence >= 1, confidence=confidence)

    def _matches_screen_ratio(self, width: int, height: int) -> bool:
        """Return True if width/height is within ±0.05 of any known screen ratio."""
        if height == 0:
            return False
        ratio = width / height
        return any(abs(ratio - r) <= _TOLERANCE for r in _ALL_RATIOS)
