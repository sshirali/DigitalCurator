"""Unit tests for DuplicateDetector."""

from __future__ import annotations

from pathlib import Path

import imagehash
import pytest

from host.duplicate_detector import DuplicateDetector
from host.models import FileRecord


def make_record(
    id: int,
    sha256: str,
    phash: str,
    file_size: int = 1000,
    laplacian_var: float | None = None,
) -> FileRecord:
    return FileRecord(
        id=id,
        abs_path=Path(f"/tmp/img_{id}.jpg"),
        file_size=file_size,
        last_modified=0.0,
        sha256=sha256,
        phash=phash,
        thumb_path=None,
        thumb_status="pending",
        is_screenshot=False,
        screenshot_conf=0,
        laplacian_var=laplacian_var,
        mean_luminance=None,
        is_blurry=False,
        is_dark=False,
        decision="undecided",
        status="active",
    )


# A known 64-bit hex pHash (all zeros = 16 hex chars for 64-bit)
HASH_A = "0000000000000000"
HASH_B = "0000000000000001"  # 1 bit different from A
HASH_C = "ffffffffffffffff"  # very far from A


class TestDuplicateDetectorExact:
    def test_exact_duplicates_grouped(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "abc123", HASH_A)
        r2 = make_record(2, "abc123", HASH_B)
        r3 = make_record(3, "def456", HASH_C)

        groups = detector.detect([r1, r2, r3])

        exact = [g for g in groups if g.group_type == "exact"]
        assert len(exact) == 1
        assert len(exact[0].members) == 2
        assert {m.id for m in exact[0].members} == {1, 2}

    def test_no_exact_duplicates_returns_empty_exact(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "aaa", HASH_A)
        r2 = make_record(2, "bbb", HASH_C)

        groups = detector.detect([r1, r2])
        exact = [g for g in groups if g.group_type == "exact"]
        assert len(exact) == 0

    def test_single_file_not_grouped(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "unique", HASH_A)
        groups = detector.detect([r1])
        assert groups == []

    def test_empty_input(self):
        detector = DuplicateDetector()
        assert detector.detect([]) == []


class TestDuplicateDetectorNear:
    def test_near_duplicates_within_threshold(self):
        detector = DuplicateDetector()
        # HASH_A and HASH_B differ by 1 bit — well within threshold of 10
        r1 = make_record(1, "aaa", HASH_A)
        r2 = make_record(2, "bbb", HASH_B)

        groups = detector.detect([r1, r2])
        near = [g for g in groups if g.group_type == "near"]
        assert len(near) == 1
        assert {m.id for m in near[0].members} == {1, 2}

    def test_far_hashes_not_grouped(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "aaa", HASH_A)
        r2 = make_record(2, "bbb", HASH_C)

        groups = detector.detect([r1, r2])
        assert groups == []

    def test_exact_duplicates_excluded_from_near(self):
        """Files already in an exact group should not appear in near groups."""
        detector = DuplicateDetector()
        r1 = make_record(1, "same", HASH_A)
        r2 = make_record(2, "same", HASH_B)  # same sha256 → exact group

        groups = detector.detect([r1, r2])
        near = [g for g in groups if g.group_type == "near"]
        assert len(near) == 0


class TestWinnerSelection:
    def test_winner_is_largest_file(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "x", HASH_A, file_size=500)
        r2 = make_record(2, "x", HASH_A, file_size=2000)
        r3 = make_record(3, "x", HASH_A, file_size=1000)

        winner = detector._select_winner([r1, r2, r3])
        assert winner.id == 2

    def test_tiebreak_by_laplacian_var(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "x", HASH_A, file_size=1000, laplacian_var=50.0)
        r2 = make_record(2, "x", HASH_A, file_size=1000, laplacian_var=200.0)

        winner = detector._select_winner([r1, r2])
        assert winner.id == 2

    def test_none_laplacian_treated_as_zero(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "x", HASH_A, file_size=1000, laplacian_var=None)
        r2 = make_record(2, "x", HASH_A, file_size=1000, laplacian_var=10.0)

        winner = detector._select_winner([r1, r2])
        assert winner.id == 2

    def test_winner_id_set_on_group(self):
        detector = DuplicateDetector()
        r1 = make_record(1, "same", HASH_A, file_size=100)
        r2 = make_record(2, "same", HASH_A, file_size=999)

        groups = detector.detect([r1, r2])
        assert len(groups) == 1
        assert groups[0].winner_id == 2
