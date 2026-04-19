"""SQLAlchemy ORM models for Digital Curator."""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    REAL,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class FileModel(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    abs_path = Column(Text, nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    last_modified = Column(REAL, nullable=False)
    sha256 = Column(Text, nullable=False)
    phash = Column(Text, nullable=False)
    thumb_path = Column(Text, nullable=True)
    thumb_status = Column(Text, nullable=False, default="pending")
    is_screenshot = Column(Integer, nullable=False, default=0)
    screenshot_conf = Column(Integer, nullable=False, default=0)
    laplacian_var = Column(REAL, nullable=True)
    mean_luminance = Column(REAL, nullable=True)
    is_blurry = Column(Integer, nullable=False, default=0)
    is_dark = Column(Integer, nullable=False, default=0)
    decision = Column(Text, nullable=False, default="undecided")
    status = Column(Text, nullable=False, default="active")

    group_memberships = relationship("GroupMemberModel", back_populates="file")


class DuplicateGroupModel(Base):
    __tablename__ = "duplicate_groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_type = Column(Text, nullable=False)  # 'exact' | 'near'

    members = relationship("GroupMemberModel", back_populates="group")


class GroupMemberModel(Base):
    __tablename__ = "group_members"

    group_id = Column(Integer, ForeignKey("duplicate_groups.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    is_winner = Column(Integer, nullable=False, default=0)

    __table_args__ = (PrimaryKeyConstraint("group_id", "file_id"),)

    group = relationship("DuplicateGroupModel", back_populates="members")
    file = relationship("FileModel", back_populates="group_memberships")
