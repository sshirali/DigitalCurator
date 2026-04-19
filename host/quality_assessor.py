"""Quality assessment for image sharpness and exposure."""

from __future__ import annotations

from pathlib import Path

import cv2

from host.models import QualityConfig, QualityResult


class QualityAssessor:
    def assess(self, path: Path, config: QualityConfig) -> QualityResult:
        """Assess image quality by computing sharpness and luminance metrics.

        Args:
            path: Path to the image file.
            config: Thresholds for blur and dark detection.

        Returns:
            QualityResult with computed metrics and flags.

        Raises:
            ValueError: If the image cannot be read (corrupt or unreadable).
        """
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Cannot read image: {path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_variance = cv2.Laplacian(gray, cv2.CV_64F).var()

        mean_luminance = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0].mean()

        is_blurry = bool(laplacian_variance < config.blur_threshold)
        is_dark = bool(mean_luminance < config.dark_threshold)

        return QualityResult(
            laplacian_variance=float(laplacian_variance),
            mean_luminance=float(mean_luminance),
            is_blurry=is_blurry,
            is_dark=is_dark,
        )
