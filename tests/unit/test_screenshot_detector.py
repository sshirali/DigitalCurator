"""Unit tests for ScreenshotDetector."""

from pathlib import Path

import pytest

from host.models import ImageMetadata, ScreenshotResult
from host.screenshot_detector import ScreenshotDetector


def make_meta(
    width: int = 1080,
    height: int = 1920,
    has_exif: bool = False,
    has_capture_date: bool = False,
    filename: str = "image.jpg",
) -> ImageMetadata:
    return ImageMetadata(
        width=width,
        height=height,
        has_exif=has_exif,
        has_capture_date=has_capture_date,
        filename=filename,
    )


@pytest.fixture
def detector() -> ScreenshotDetector:
    return ScreenshotDetector()


PATH = Path("/some/image.jpg")


class TestCriterion1:
    """No EXIF + matching aspect ratio."""

    def test_no_exif_and_9_16_ratio_scores_1(self, detector):
        meta = make_meta(width=1080, height=1920, has_exif=False, has_capture_date=True)
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1
        assert result.is_candidate

    def test_has_exif_does_not_trigger_criterion1(self, detector):
        # has_exif=True means criterion 1 should NOT fire
        meta = make_meta(width=1080, height=1920, has_exif=True, has_capture_date=True, filename="photo.jpg")
        result = detector.classify(PATH, meta)
        assert result.confidence == 0
        assert not result.is_candidate

    def test_no_exif_but_non_screen_ratio_does_not_trigger(self, detector):
        # 1:1 ratio is not a screen ratio
        meta = make_meta(width=1000, height=1000, has_exif=False, has_capture_date=True, filename="photo.jpg")
        result = detector.classify(PATH, meta)
        assert result.confidence == 0

    def test_landscape_9_16_ratio_triggers(self, detector):
        # Landscape inverse: 16/9
        meta = make_meta(width=1920, height=1080, has_exif=False, has_capture_date=True, filename="photo.jpg")
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1

    def test_ratio_within_tolerance_triggers(self, detector):
        # 9/16 = 0.5625; add tolerance 0.04 → 0.6025 still within ±0.05
        meta = make_meta(width=603, height=1000, has_exif=False, has_capture_date=True, filename="photo.jpg")
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1

    def test_ratio_outside_tolerance_does_not_trigger(self, detector):
        # 4:3 ratio = 1.333; nearest screen ratio is 3/2=1.5, diff=0.167 > 0.05
        meta = make_meta(width=400, height=300, has_exif=False, has_capture_date=True, filename="photo.jpg")
        result = detector.classify(PATH, meta)
        assert result.confidence == 0


class TestCriterion2:
    """Filename contains 'screenshot'."""

    def test_filename_screenshot_lowercase(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=True, filename="screenshot_001.png", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1
        assert result.is_candidate

    def test_filename_screenshot_uppercase(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=True, filename="SCREENSHOT.PNG", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1

    def test_filename_screenshot_mixed_case(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=True, filename="MyScreenShot.jpg", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1

    def test_filename_without_screenshot_does_not_trigger(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=True, filename="photo.jpg", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence == 0


class TestCriterion3:
    """No EXIF capture date."""

    def test_no_capture_date_scores_1(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=False, filename="photo.jpg", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence >= 1
        assert result.is_candidate

    def test_has_capture_date_does_not_trigger(self, detector):
        meta = make_meta(has_exif=True, has_capture_date=True, filename="photo.jpg", width=100, height=100)
        result = detector.classify(PATH, meta)
        assert result.confidence == 0


class TestConfidenceScoring:
    """Confidence accumulates correctly across criteria."""

    def test_all_three_criteria_gives_confidence_3(self, detector):
        # criterion 1: no exif + screen ratio (9:16)
        # criterion 2: filename has "screenshot"
        # criterion 3: no capture date
        meta = make_meta(
            width=1080, height=1920,
            has_exif=False, has_capture_date=False,
            filename="screenshot_2024.png",
        )
        result = detector.classify(PATH, meta)
        assert result.confidence == 3
        assert result.is_candidate

    def test_two_criteria_gives_confidence_2(self, detector):
        # criterion 2 + criterion 3
        meta = make_meta(
            width=100, height=100,
            has_exif=True, has_capture_date=False,
            filename="screenshot.jpg",
        )
        result = detector.classify(PATH, meta)
        assert result.confidence == 2

    def test_zero_criteria_gives_confidence_0_not_candidate(self, detector):
        meta = make_meta(
            width=100, height=100,
            has_exif=True, has_capture_date=True,
            filename="photo.jpg",
        )
        result = detector.classify(PATH, meta)
        assert result.confidence == 0
        assert not result.is_candidate

    def test_higher_criteria_count_gives_higher_confidence(self, detector):
        one_match = make_meta(has_exif=True, has_capture_date=False, filename="photo.jpg", width=100, height=100)
        two_match = make_meta(has_exif=True, has_capture_date=False, filename="screenshot.jpg", width=100, height=100)
        r1 = detector.classify(PATH, one_match)
        r2 = detector.classify(PATH, two_match)
        assert r2.confidence > r1.confidence

    def test_returns_screenshot_result_type(self, detector):
        meta = make_meta()
        result = detector.classify(PATH, meta)
        assert isinstance(result, ScreenshotResult)

    def test_known_screen_ratios(self, detector):
        """All three known portrait ratios should trigger criterion 1."""
        ratios = [(9, 19.5), (9, 16), (2, 3)]
        for w_part, h_part in ratios:
            scale = 100
            w = int(w_part * scale)
            h = int(h_part * scale)
            meta = make_meta(width=w, height=h, has_exif=False, has_capture_date=True, filename="photo.jpg")
            result = detector.classify(PATH, meta)
            assert result.confidence >= 1, f"Expected ratio {w_part}:{h_part} to trigger criterion 1"
