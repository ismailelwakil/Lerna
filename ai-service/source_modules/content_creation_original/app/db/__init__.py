"""Database engine/session (graceful fallback: unreachable DATABASE_URL →
SQLite in dev so the module always runs; production fails fast)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..core.config import DATA_DIR, get_settings
from ..core.logging import get_logger

log = get_logger("db")


class Base(DeclarativeBase):
    pass


def make_engine():
    settings = get_settings()
    url = settings.database_url
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args=(
            {"check_same_thread": False} if url.startswith("sqlite") else {}))
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("db_connected", extra={"ctx": {"dialect": url.split(':')[0]}})
        return engine
    except Exception as exc:  # noqa: BLE001
        if settings.is_prod:
            raise
        fallback = f"sqlite:///{(DATA_DIR / 'content.db').as_posix()}"
        log.warning("db_unreachable_fallback_sqlite",
                    extra={"ctx": {"err": str(exc)[:200]}})
        engine = create_engine(fallback, connect_args={"check_same_thread": False})
        return engine


class Database:
    def __init__(self) -> None:
        self.engine = make_engine()
        if self.engine.url.get_backend_name() == "sqlite":
            Path(str(self.engine.url).split("///")[-1]).parent.mkdir(parents=True, exist_ok=True)

            @event.listens_for(self.engine, "connect")
            def _pragmas(dbapi_connection, _record):  # pragma: no cover
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.close()
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init(self) -> None:
        from . import models  # noqa: F401 — register tables on Base
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_database = None


def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database()
    return _database


def set_database(db: Database) -> None:
    global _database
    _database = db