"""Unit tests for DataManager.wipe()."""

import shutil
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


def _make_data_manager(db_path: Path, thumbs_dir: Path):
    """Import DataManager with patched dependencies to avoid broken schema."""
    # Stub out host.db.init so schema.py is never imported
    db_init_stub = ModuleType("host.db.init")
    db_init_stub.get_db_path = lambda: db_path  # type: ignore[attr-defined]

    thumb_stub = ModuleType("host.thumbnail_generator")
    thumb_stub.THUMB_DIR = thumbs_dir  # type: ignore[attr-defined]

    with patch.dict(sys.modules, {
        "host.db.init": db_init_stub,
        "host.thumbnail_generator": thumb_stub,
    }):
        # Force re-import with patched modules
        if "host.data_manager" in sys.modules:
            del sys.modules["host.data_manager"]
        from host.data_manager import DataManager  # noqa: PLC0415
        return DataManager()


def test_wipe_deletes_db_and_thumbs(tmp_path):
    db_file = tmp_path / "curator.db"
    thumbs_dir = tmp_path / "thumbs"
    db_file.write_text("data")
    thumbs_dir.mkdir()
    (thumbs_dir / "a.jpg").write_text("img")

    dm = _make_data_manager(db_file, thumbs_dir)
    dm.wipe()

    assert not db_file.exists()
    assert not thumbs_dir.exists()


def test_wipe_is_idempotent(tmp_path):
    db_file = tmp_path / "curator.db"
    thumbs_dir = tmp_path / "thumbs"
    # Neither exists — should not raise

    dm = _make_data_manager(db_file, thumbs_dir)
    dm.wipe()
    dm.wipe()


def test_wipe_does_not_touch_original_images(tmp_path):
    db_file = tmp_path / "curator.db"
    thumbs_dir = tmp_path / "thumbs"
    originals_dir = tmp_path / "photos"
    originals_dir.mkdir()
    original = originals_dir / "photo.jpg"
    original.write_text("original")

    dm = _make_data_manager(db_file, thumbs_dir)
    dm.wipe()

    assert original.exists()
