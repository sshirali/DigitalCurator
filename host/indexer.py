"""Indexer: wraps SQLAlchemy session management for all DB writes/reads."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from host.db.init import get_session
from host.db.schema import DuplicateGroupModel, FileModel, GroupMemberModel

if TYPE_CHECKING:
    from host.models import Category, Decision, DuplicateGroup, FileRecord


def _orm_to_file_record(row: FileModel) -> "FileRecord":
    from host.models import FileRecord

    return FileRecord(
        id=row.id,
        abs_path=Path(row.abs_path),
        file_size=row.file_size,
        last_modified=row.last_modified,
        sha256=row.sha256,
        phash=row.phash,
        thumb_path=Path(row.thumb_path) if row.thumb_path else None,
        thumb_status=row.thumb_status,
        is_screenshot=bool(row.is_screenshot),
        screenshot_conf=row.screenshot_conf,
        laplacian_var=row.laplacian_var,
        mean_luminance=row.mean_luminance,
        is_blurry=bool(row.is_blurry),
        is_dark=bool(row.is_dark),
        decision=row.decision,
        status=row.status,
    )


def _file_record_to_orm(record: "FileRecord", row: FileModel) -> None:
    """Write all fields from *record* into an existing ORM *row* in-place."""
    row.abs_path = str(record.abs_path)
    row.file_size = record.file_size
    row.last_modified = record.last_modified
    row.sha256 = record.sha256
    row.phash = record.phash
    row.thumb_path = str(record.thumb_path) if record.thumb_path else None
    row.thumb_status = record.thumb_status
    row.is_screenshot = int(record.is_screenshot)
    row.screenshot_conf = record.screenshot_conf
    row.laplacian_var = record.laplacian_var
    row.mean_luminance = record.mean_luminance
    row.is_blurry = int(record.is_blurry)
    row.is_dark = int(record.is_dark)
    row.decision = record.decision
    row.status = record.status


class Indexer:
    """All database writes and reads go through this class."""

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    def upsert_file(self, record: "FileRecord") -> None:
        """Insert or update a file record in the DB."""
        session = get_session()
        try:
            row = (
                session.query(FileModel)
                .filter_by(abs_path=str(record.abs_path))
                .first()
            )
            if row is None:
                row = FileModel()
                _file_record_to_orm(record, row)
                session.add(row)
            else:
                _file_record_to_orm(record, row)
            session.commit()
            # Back-fill the auto-generated id onto the dataclass.
            session.refresh(row)
            record.id = row.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upsert_group(self, group: "DuplicateGroup") -> None:
        """Insert or update a duplicate group and its members."""
        session = get_session()
        try:
            if group.id is not None:
                grp_row = session.get(DuplicateGroupModel, group.id)
            else:
                grp_row = None

            if grp_row is None:
                grp_row = DuplicateGroupModel(group_type=group.group_type)
                session.add(grp_row)
                session.flush()  # populate grp_row.id
            else:
                grp_row.group_type = group.group_type

            group.id = grp_row.id

            # Rebuild membership rows.
            session.query(GroupMemberModel).filter_by(
                group_id=grp_row.id
            ).delete()

            for member in group.members:
                is_winner = int(
                    member.id is not None and member.id == group.winner_id
                )
                member_row = GroupMemberModel(
                    group_id=grp_row.id,
                    file_id=member.id,
                    is_winner=is_winner,
                )
                session.add(member_row)

            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_decision(self, file_id: int, decision: "Decision") -> None:
        """Update the decision field for a file."""
        session = get_session()
        try:
            row = session.get(FileModel, file_id)
            if row is None:
                raise ValueError(f"No file with id={file_id}")
            if hasattr(decision, "value"):
                row.decision = decision.value
            else:
                row.decision = str(decision)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def set_trashed(self, file_id: int) -> None:
        """Update the status field to 'trashed' for a file."""
        session = get_session()
        try:
            row = session.get(FileModel, file_id)
            if row is None:
                raise ValueError(f"No file with id={file_id}")
            row.status = "trashed"
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_flagged(self, category: "Category") -> list["FileRecord"]:
        """Return all files flagged for a category.

        - duplicates  → files that appear in any duplicate group
        - screenshots → is_screenshot = 1
        - blurry      → is_blurry = 1 OR is_dark = 1
        """
        from host.models import Category

        session = get_session()
        try:
            if category == Category.duplicates:
                subq = (
                    session.query(GroupMemberModel.file_id)
                    .distinct()
                    .subquery()
                )
                rows = (
                    session.query(FileModel)
                    .filter(FileModel.id.in_(subq))
                    .all()
                )
            elif category == Category.screenshots:
                rows = (
                    session.query(FileModel)
                    .filter(FileModel.is_screenshot == 1)
                    .all()
                )
            elif category == Category.blurry:
                rows = (
                    session.query(FileModel)
                    .filter(
                        (FileModel.is_blurry == 1)
                        | (FileModel.is_dark == 1)
                    )
                    .all()
                )
            else:
                rows = []
            return [_orm_to_file_record(r) for r in rows]
        finally:
            session.close()

    def get_group(self, group_id: int) -> "DuplicateGroup":
        """Return a duplicate group with all members."""
        from host.models import DuplicateGroup

        session = get_session()
        try:
            grp_row = session.get(DuplicateGroupModel, group_id)
            if grp_row is None:
                raise ValueError(f"No group with id={group_id}")

            member_rows = (
                session.query(GroupMemberModel)
                .filter_by(group_id=group_id)
                .all()
            )

            members: list[FileRecord] = []
            winner_id: int | None = None
            for m in member_rows:
                file_row = session.get(FileModel, m.file_id)
                if file_row is not None:
                    members.append(_orm_to_file_record(file_row))
                if m.is_winner:
                    winner_id = m.file_id

            return DuplicateGroup(
                id=grp_row.id,
                group_type=grp_row.group_type,
                members=members,
                winner_id=winner_id,
            )
        finally:
            session.close()

    def get_file(self, abs_path: str) -> "FileRecord | None":
        """Return a file record by absolute path, or None if not found."""
        session = get_session()
        try:
            row = (
                session.query(FileModel)
                .filter_by(abs_path=abs_path)
                .first()
            )
            return _orm_to_file_record(row) if row is not None else None
        finally:
            session.close()

    def get_file_by_id(self, file_id: int) -> "FileRecord | None":
        """Return a file record by its primary key, or None if not found."""
        session = get_session()
        try:
            row = session.get(FileModel, file_id)
            return _orm_to_file_record(row) if row is not None else None
        finally:
            session.close()
