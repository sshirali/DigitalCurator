"""Thumbnail generation for Digital Curator MVP."""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from host.models import FileRecord

logger = logging.getLogger(__name__)

THUMB_DIR = Path.home() / ".digital-curator" / "thumbs"
MAX_DIM = 400


class ThumbnailGenerator:
    def generate(self, source: Path, dest: Path) -> bool:
        """Generate a stripped JPEG thumbnail (max 400px longest side).

        Returns True on success, False on failure. On failure, any partial
        file at dest is removed.
        """
        try:
            with Image.open(source) as img:
                img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)
                # Strip EXIF: convert to bytes and reload without metadata
                buf = io.BytesIO()
                img.save(buf, format="PNG")  # PNG has no EXIF
                buf.seek(0)
                clean = Image.open(buf)
                clean.load()
                dest.parent.mkdir(parents=True, exist_ok=True)
                clean.save(dest, format="JPEG")
            return True
        except Exception as exc:
            logger.warning("Failed to generate thumbnail for %s: %s", source, exc)
            if dest.exists():
                dest.unlink()
            return False

    def get_or_create(self, record: FileRecord) -> Optional[Path]:
        """Return cached thumbnail path, generating it if needed."""
        cache_path = THUMB_DIR / f"{record.sha256[:16]}.jpg"
        meta_path = cache_path.with_suffix(".meta")

        # Reuse if thumb exists and last_modified matches
        if cache_path.exists() and meta_path.exists():
            try:
                stored_mtime = float(meta_path.read_text().strip())
                if stored_mtime == record.last_modified:
                    return cache_path
            except (ValueError, OSError):
                pass

        if self.generate(record.abs_path, cache_path):
            try:
                meta_path.write_text(str(record.last_modified))
            except OSError as exc:
                logger.warning("Could not write thumbnail meta for %s: %s", cache_path, exc)
            return cache_path

        return None
