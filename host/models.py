"""Core data models for Digital Curator MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Category(str, Enum):
    duplicates = "duplicates"
    screenshots = "screenshots"
    blurry = "blurry"


class Decision(str, Enum):
    undecided = "undecided"
    keep = "keep"
    delete = "delete"


@dataclass
class ImageMetadata:
    """EXIF and image dimension info extracted from a file."""
    width: int
    height: int
    has_exif: bool
    has_capture_date: bool
    filename: str


@dataclass
class FileRecord:
    id: int | None
    abs_path: Path
    file_size: int
    last_modified: float
    sha256: str
    phash: str
    thumb_path: Path | None
    thumb_status: str          # 'pending' | 'ok' | 'unavailable'
    is_screenshot: bool
    screenshot_conf: int       # 0-3
    laplacian_var: float | None
    mean_luminance: float | None
    is_blurry: bool
    is_dark: bool
    decision: str              # 'undecided' | 'keep' | 'delete'
    status: str                # 'active' | 'trashed'


@dataclass
class DuplicateGroup:
    id: int | None
    group_type: str            # 'exact' | 'near'
    members: list[FileRecord]
    winner_id: int | None


@dataclass
class ScreenshotResult:
    """Result from ScreenshotDetector.classify()."""
    is_candidate: bool
    confidence: int            # 0-3


@dataclass
class QualityResult:
    """Result from QualityAssessor.assess()."""
    laplacian_variance: float
    mean_luminance: float
    is_blurry: bool
    is_dark: bool


@dataclass
class QualityConfig:
    blur_threshold: float = 100.0
    dark_threshold: float = 30.0


@dataclass
class ScanResult:
    """Result of a full scan operation."""
    total_files: int
    indexed_files: int
    failed_files: int
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)


@dataclass
class FailedFile:
    """A file that failed to be trashed."""
    file_id: int
    abs_path: Path
    error: str


@dataclass
class TrashResult:
    """Result of a trash operation."""
    trashed: list[int]
    failed: list[FailedFile]


@dataclass
class DecisionPayload:
    file_id: int
    decision: str              # 'keep' | 'delete'
    timestamp: float           # Unix timestamp
