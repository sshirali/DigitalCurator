"""Unit tests for QualityAssessor."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from host.models import QualityConfig, QualityResult
from host.quality_assessor import QualityAssessor


@pytest.fixture
def assessor() -> QualityAssessor:
    return QualityAssessor()


@pytest.fixture
def default_config() -> QualityConfig:
    return QualityConfig()


def write_image(path: Path, img: np.ndarray) -> None:
    cv2.imwrite(str(path), img)


class TestAssessReturnsQualityResult:
    def test_returns_quality_result_type(self, assessor, default_config, tmp_path):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "img.jpg"
        write_image(p, img)
        result = assessor.assess(p, default_config)
        assert isinstance(result, QualityResult)

    def test_laplacian_variance_is_non_negative(self, assessor, default_config, tmp_path):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "img.jpg"
        write_image(p, img)
        result = assessor.assess(p, default_config)
        assert result.laplacian_variance >= 0.0

    def test_mean_luminance_is_non_negative(self, assessor, default_config, tmp_path):
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "img.jpg"
        write_image(p, img)
        result = assessor.assess(p, default_config)
        assert result.mean_luminance >= 0.0


class TestBlurDetection:
    def test_flat_image_is_blurry(self, assessor, tmp_path):
        """A uniform image has zero Laplacian variance — always blurry."""
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "flat.jpg"
        write_image(p, img)
        config = QualityConfig(blur_threshold=100.0)
        result = assessor.assess(p, config)
        assert result.is_blurry is True

    def test_sharp_image_is_not_blurry(self, assessor, tmp_path):
        """A checkerboard has high Laplacian variance — not blurry."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[::2, ::2] = 255
        p = tmp_path / "sharp.jpg"
        write_image(p, img)
        config = QualityConfig(blur_threshold=100.0)
        result = assessor.assess(p, config)
        assert result.is_blurry is False

    def test_blur_threshold_boundary(self, assessor, tmp_path):
        """Setting threshold to 0 means nothing is blurry."""
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "flat.jpg"
        write_image(p, img)
        config = QualityConfig(blur_threshold=0.0)
        result = assessor.assess(p, config)
        assert result.is_blurry is False


class TestDarkDetection:
    def test_black_image_is_dark(self, assessor, tmp_path):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        p = tmp_path / "black.jpg"
        write_image(p, img)
        config = QualityConfig(dark_threshold=30.0)
        result = assessor.assess(p, config)
        assert result.is_dark is True

    def test_bright_image_is_not_dark(self, assessor, tmp_path):
        img = np.full((100, 100, 3), 200, dtype=np.uint8)
        p = tmp_path / "bright.jpg"
        write_image(p, img)
        config = QualityConfig(dark_threshold=30.0)
        result = assessor.assess(p, config)
        assert result.is_dark is False

    def test_dark_threshold_boundary(self, assessor, tmp_path):
        """Setting threshold to 0 means nothing is dark."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        p = tmp_path / "black.jpg"
        write_image(p, img)
        config = QualityConfig(dark_threshold=0.0)
        result = assessor.assess(p, config)
        assert result.is_dark is False


class TestUnreadableImage:
    def test_missing_file_raises(self, assessor, default_config, tmp_path):
        p = tmp_path / "nonexistent.jpg"
        with pytest.raises(ValueError, match="Cannot read image"):
            assessor.assess(p, default_config)

    def test_corrupt_file_raises(self, assessor, default_config, tmp_path):
        p = tmp_path / "corrupt.jpg"
        p.write_bytes(b"not an image")
        with pytest.raises(ValueError, match="Cannot read image"):
            assessor.assess(p, default_config)


class TestConfigurableThresholds:
    def test_custom_blur_threshold(self, assessor, tmp_path):
        """Flat image (var=0) is blurry only when threshold > 0."""
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        p = tmp_path / "flat.jpg"
        write_image(p, img)

        result_strict = assessor.assess(p, QualityConfig(blur_threshold=1.0))
        result_zero = assessor.assess(p, QualityConfig(blur_threshold=0.0))

        assert result_strict.is_blurry is True
        assert result_zero.is_blurry is False

    def test_custom_dark_threshold(self, assessor, tmp_path):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        p = tmp_path / "black.jpg"
        write_image(p, img)

        result_strict = assessor.assess(p, QualityConfig(dark_threshold=1.0))
        result_zero = assessor.assess(p, QualityConfig(dark_threshold=0.0))

        assert result_strict.is_dark is True
        assert result_zero.is_dark is False
