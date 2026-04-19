"""TrashManager: moves files to the OS Trash/Recycle Bin via send2trash."""

from __future__ import annotations

import logging
from pathlib import Path

import send2trash

from host.models import FailedFile, TrashResult

logger = logging.getLogger(__name__)


class TrashManager:
    def __init__(self, indexer=None) -> None:
        if indexer is None:
            from host.indexer import Indexer
            indexer = Indexer()
        self._indexer = indexer

    def trash_files(self, file_ids: list[int]) -> TrashResult:
        """Move each file to the OS Trash and update the DB on success.

        Returns a TrashResult with the IDs of successfully trashed files and
        a list of FailedFile entries for any files that could not be trashed.
        """
        trashed: list[int] = []
        failed: list[FailedFile] = []

        for file_id in file_ids:
            record = self._indexer.get_file_by_id(file_id)
            if record is None:
                logger.error(
                    "trash_files: no record found for file_id=%d", file_id
                )
                failed.append(
                    FailedFile(
                        file_id=file_id,
                        abs_path=Path(""),
                        error=f"No file record found for id={file_id}",
                    )
                )
                continue

            abs_path: Path = record.abs_path
            try:
                send2trash.send2trash(str(abs_path))
                self._indexer.set_trashed(file_id)
                trashed.append(file_id)
            except Exception as exc:
                logger.error(
                    "trash_files: failed to trash %s: %s", abs_path, exc
                )
                failed.append(
                    FailedFile(
                        file_id=file_id,
                        abs_path=abs_path,
                        error=str(exc),
                    )
                )

        return TrashResult(trashed=trashed, failed=failed)
