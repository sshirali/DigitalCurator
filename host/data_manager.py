"""Data management for Digital Curator MVP."""

import shutil

from host.db.init import get_db_path
from host.thumbnail_generator import THUMB_DIR


class DataManager:
    def wipe(self) -> None:
        """Delete the SQLite DB and thumbnail cache. Idempotent."""
        get_db_path().unlink(missing_ok=True)
        if THUMB_DIR.exists():
            shutil.rmtree(THUMB_DIR)
