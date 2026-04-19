"""Database initialization for Digital Curator."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from host.db.schema import Base

_APP_DIR = Path.home() / ".digital-curator"
_DB_PATH = _APP_DIR / "curator.db"

_engine = None
_SessionLocal = None


def get_db_path() -> Path:
    return _DB_PATH


def init_db(db_path: Path | None = None) -> None:
    """Create the app directory and initialize the SQLite database."""
    global _engine, _SessionLocal

    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def get_engine():
    if _engine is None:
        init_db()
    return _engine


def get_session():
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
