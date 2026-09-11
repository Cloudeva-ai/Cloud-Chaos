"""
database.py — Robust SQLAlchemy ORM + CRUD layer for Cloud Chaos.

Schema
──────
players         — one row per unique registrant
game_sessions   — one row per completed game attempt (FK → players)
selections      — one row per pain·column selection (FK → game_sessions)
events          — audit / analytics log for every meaningful action

All timestamps are stored as UTC ISO-8601 strings for portability.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import tempfile
from functools import lru_cache
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from game_data import NUM_PAINS

# ─────────────────────────────────────────────────────────────
#  ENGINE SETUP
# ─────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
DEFAULT_DATA_DIR_NAME = ".cloud_chaos_data"


def _is_writable_directory(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe_path = path / ".write_test"
        probe_path.write_text("ok", encoding="ascii")
        probe_path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _resolve_data_dir() -> Path:
    env_dir = os.getenv("CLOUD_CHAOS_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    repo_data_dir = APP_DIR / DEFAULT_DATA_DIR_NAME
    if _is_writable_directory(repo_data_dir):
        return repo_data_dir

    return (Path(tempfile.gettempdir()) / "cloud_chaos").resolve()


DATA_DIR = _resolve_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

LEGACY_DB_PATH = APP_DIR / "cloud_chaos.db"
LEGACY_DB_WAL_PATH = APP_DIR / "cloud_chaos.db-wal"
LEGACY_DB_SHM_PATH = APP_DIR / "cloud_chaos.db-shm"
LEGACY_REGISTRATION_BACKUP_PATH = APP_DIR / "player_registrations_backup.xlsx"
LEGACY_REGISTRATION_BACKUP_CSV_PATH = APP_DIR / "player_registrations_backup.csv"
LEGACY_REGISTRATION_BACKUP_DIR = APP_DIR / "registration_backups"

DB_PATH = DATA_DIR / "cloud_chaos.db"
REGISTRATION_BACKUP_PATH = DATA_DIR / "player_registrations_backup.xlsx"
REGISTRATION_BACKUP_CSV_PATH = DATA_DIR / "player_registrations_backup.csv"
REGISTRATION_FAILOVER_PATH = DATA_DIR / "player_registrations_failover.xlsx"
REGISTRATION_FAILOVER_CSV_PATH = DATA_DIR / "player_registrations_failover.csv"
GAME_SESSION_FAILOVER_PATH = DATA_DIR / "game_sessions_failover.xlsx"
GAME_SESSION_FAILOVER_CSV_PATH = DATA_DIR / "game_sessions_failover.csv"
REGISTRATION_BACKUP_DIR = DATA_DIR / "registration_backups"
BACKUP_LOCK = threading.Lock()
BACKUP_MIN_INTERVAL_SECONDS = 10
SNAPSHOT_MIN_INTERVAL_SECONDS = 300
_last_backup_export_at = 0.0
_last_snapshot_export_at = 0.0
_last_game_sessions_export_at = 0.0

GAME_SESSIONS_BACKUP_PATH = DATA_DIR / "game_sessions_backup.xlsx"
GAME_SESSIONS_BACKUP_CSV_PATH = DATA_DIR / "game_sessions_backup.csv"
SELECTIONS_BACKUP_PATH = DATA_DIR / "game_selections_backup.xlsx"
SELECTIONS_BACKUP_CSV_PATH = DATA_DIR / "game_selections_backup.csv"
ADMIN_EXPORT_PATH = DATA_DIR / "cloud_chaos_admin_export.xlsx"


def _repair_database() -> None:
    """Attempt to repair corrupted database files."""
    # Remove WAL files if they exist (can cause I/O issues)
    wal_path = DB_PATH.with_suffix(f"{DB_PATH.suffix}-wal")
    shm_path = DB_PATH.with_suffix(f"{DB_PATH.suffix}-shm")
    
    for path in [wal_path, shm_path]:
        if path.exists():
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    
    # Try to vacuum and repair
    if DB_PATH.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH), timeout=10)
            conn.execute("PRAGMA integrity_check;")
            conn.execute("VACUUM;")
            conn.close()
        except Exception:
            # If repair fails, move the corrupted file and start fresh
            try:
                backup_path = DB_PATH.with_stem(f"{DB_PATH.stem}_corrupted_{int(time.time())}")
                shutil.move(str(DB_PATH), str(backup_path))
            except OSError:
                pass


def _copy_if_missing(source: Path, target: Path) -> None:
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _migrate_legacy_files() -> None:
    if DATA_DIR == APP_DIR:
        return

    _copy_if_missing(LEGACY_DB_PATH, DB_PATH)
    _copy_if_missing(LEGACY_DB_WAL_PATH, DB_PATH.with_name(f"{DB_PATH.name}-wal"))
    _copy_if_missing(LEGACY_DB_SHM_PATH, DB_PATH.with_name(f"{DB_PATH.name}-shm"))
    _copy_if_missing(LEGACY_REGISTRATION_BACKUP_PATH, REGISTRATION_BACKUP_PATH)
    _copy_if_missing(LEGACY_REGISTRATION_BACKUP_CSV_PATH, REGISTRATION_BACKUP_CSV_PATH)

    if LEGACY_REGISTRATION_BACKUP_DIR.exists() and not REGISTRATION_BACKUP_DIR.exists():
        shutil.copytree(LEGACY_REGISTRATION_BACKUP_DIR, REGISTRATION_BACKUP_DIR)


_migrate_legacy_files()

# Attempt repair before creating engine
_repair_database()

ENGINE  = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 60},
    echo=False,
)

# Enable WAL mode and foreign keys on every new connection
@event.listens_for(ENGINE, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=DELETE;")  # Use DELETE instead of WAL to avoid I/O issues
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=90000;")  # 90 seconds
        cursor.execute("PRAGMA temp_store=MEMORY;")
        cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache
    except Exception:
        pass
    finally:
        cursor.close()

SessionFactory = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


# ─────────────────────────────────────────────────────────────
#  ORM MODELS
# ─────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Player(Base):
    """
    One row per unique player registration.
    A player can have many game sessions.
    """
    __tablename__ = "players"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_player_name_non_empty"),
        CheckConstraint("length(trim(company)) > 0", name="ck_player_company_non_empty"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(120), nullable=False)
    company     = Column(String(120), nullable=False)
    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    last_seen   = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
    total_plays = Column(Integer, default=0, nullable=False)
    best_score  = Column(Integer, default=0, nullable=False)
    best_time   = Column(Integer, nullable=True)   # seconds for the best-score run

    sessions = relationship("GameSession", back_populates="player",
                            cascade="all, delete-orphan", lazy="select")
    events   = relationship("Event", back_populates="player",
                            cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<Player id={self.id} name={self.name!r} company={self.company!r}>"


class GameSession(Base):
    """
    One row per completed (or timed-out) game attempt.
    Stores aggregate result + metadata.
    """
    __tablename__ = "game_sessions"
    __table_args__ = (
        Index("ix_session_player", "player_id"),
        Index("ix_session_score_time", "score", "time_used"),
        CheckConstraint("score >= 0", name="ck_session_score_non_negative"),
        CheckConstraint("time_used >= 0", name="ck_session_time_non_negative"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    player_id    = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    score        = Column(Integer,  nullable=False, default=0)
    time_used    = Column(Integer,  nullable=False, default=90)   # seconds
    completed_at = Column(DateTime(timezone=True), default=_now,  nullable=False)
    timed_out    = Column(Boolean,  nullable=False, default=False)
    # Derived flags stored for fast query
    is_perfect   = Column(Boolean,  nullable=False, default=False)

    player     = relationship("Player",    back_populates="sessions")
    selections = relationship("Selection", back_populates="session",
                              cascade="all, delete-orphan", lazy="select")

    def __repr__(self):
        return f"<GameSession id={self.id} player_id={self.player_id} score={self.score}>"


class Selection(Base):
    """
    One row per pain point per session — detailed answer tracking.
    Stores both what the player picked and whether it was correct.
    """
    __tablename__ = "selections"
    __table_args__ = (
        Index("ix_selection_session", "session_id"),
        UniqueConstraint("session_id", "pain_idx", name="uq_selection_per_pain"),
        CheckConstraint("pain_idx >= 0", name="ck_selection_pain_non_negative"),
    )

    id               = Column(Integer, primary_key=True, autoincrement=True)
    session_id       = Column(Integer, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False)
    pain_idx         = Column(Integer, nullable=False)  # 0-4
    owner_orig_idx   = Column(Integer, nullable=True)   # which owner was chosen (orig index)
    impact_orig_idx  = Column(Integer, nullable=True)   # which impact was chosen (orig index)
    owner_correct    = Column(Boolean, nullable=False, default=False)
    impact_correct   = Column(Boolean, nullable=False, default=False)
    both_correct     = Column(Boolean, nullable=False, default=False)

    session = relationship("GameSession", back_populates="selections")

    def __repr__(self):
        return (f"<Selection session={self.session_id} pain={self.pain_idx} "
                f"ok={self.both_correct}>")


class Event(Base):
    """
    Lightweight audit / analytics log.
    Records every significant player action with a JSON-friendly payload.
    """
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_event_player", "player_id"),
        Index("ix_event_type",   "event_type"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    player_id   = Column(Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    event_type  = Column(String(60),  nullable=False)   # e.g. "game_start", "game_submit"
    payload     = Column(Text,        nullable=True)     # JSON string for extra context
    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)

    player = relationship("Player", back_populates="events")

    def __repr__(self):
        return f"<Event id={self.id} type={self.event_type!r} player={self.player_id}>"


# ─────────────────────────────────────────────────────────────
#  INITIALISATION
# ─────────────────────────────────────────────────────────────
def _migrate_players_table_drop_email() -> None:
    """Rebuild legacy players tables that still contain an email column."""
    with ENGINE.begin() as conn:
        table_exists = conn.execute(text("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'players'
        """)).scalar()
        if not table_exists:
            return

        columns = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(players)")).fetchall()
        }
        if "email" not in columns:
            return

        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(text("""
            CREATE TABLE players__new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(120) NOT NULL,
                company VARCHAR(120) NOT NULL,
                created_at DATETIME NOT NULL,
                last_seen DATETIME NOT NULL,
                total_plays INTEGER NOT NULL,
                best_score INTEGER NOT NULL,
                best_time INTEGER,
                CONSTRAINT ck_player_name_non_empty CHECK (length(trim(name)) > 0),
                CONSTRAINT ck_player_company_non_empty CHECK (length(trim(company)) > 0)
            )
        """))
        conn.execute(text("""
            INSERT INTO players__new (
                id, name, company, created_at, last_seen, total_plays, best_score, best_time
            )
            SELECT
                id, name, company, created_at, last_seen, total_plays, best_score, best_time
            FROM players
        """))
        conn.execute(text("DROP TABLE players"))
        conn.execute(text("ALTER TABLE players__new RENAME TO players"))
        conn.execute(text("PRAGMA foreign_keys=ON"))


def _drop_email_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["email"], errors="ignore")


def _rewrite_excel_without_email(path: Path) -> None:
    sheets = pd.read_excel(path, sheet_name=None)
    temp_path = path.with_suffix(".tmp.xlsx")
    with pd.ExcelWriter(temp_path) as writer:
        for sheet_name, sheet_df in sheets.items():
            _drop_email_columns(sheet_df).to_excel(writer, index=False, sheet_name=sheet_name)
    os.replace(temp_path, path)


def _rewrite_csv_without_email(path: Path) -> None:
    df = pd.read_csv(path)
    temp_path = path.with_suffix(".tmp.csv")
    _drop_email_columns(df).to_csv(temp_path, index=False)
    os.replace(temp_path, path)


def _scrub_email_from_backup_exports() -> None:
    candidate_paths: set[Path] = {
        LEGACY_REGISTRATION_BACKUP_PATH,
        LEGACY_REGISTRATION_BACKUP_CSV_PATH,
        REGISTRATION_BACKUP_PATH,
        REGISTRATION_BACKUP_CSV_PATH,
        REGISTRATION_FAILOVER_PATH,
        REGISTRATION_FAILOVER_CSV_PATH,
        GAME_SESSIONS_BACKUP_PATH,
        GAME_SESSIONS_BACKUP_CSV_PATH,
    }

    for directory in (
        LEGACY_REGISTRATION_BACKUP_DIR,
        REGISTRATION_BACKUP_DIR,
        DATA_DIR,
    ):
        if directory.exists():
            candidate_paths.update(path for path in directory.rglob("*.csv"))
            candidate_paths.update(path for path in directory.rglob("*.xlsx"))

    for path in sorted(candidate_paths):
        if not path.exists():
            continue
        try:
            if path.suffix.lower() == ".csv":
                _rewrite_csv_without_email(path)
            elif path.suffix.lower() == ".xlsx":
                _rewrite_excel_without_email(path)
        except Exception:
            continue


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call on every startup."""
    try:
        _migrate_players_table_drop_email()
        Base.metadata.create_all(ENGINE)
        _scrub_email_from_backup_exports()
    except Exception as e:
        # If creation fails, try to repair and retry once
        if "disk I/O" in str(e).lower() or "database is locked" in str(e).lower():
            _repair_database()
            try:
                _migrate_players_table_drop_email()
                Base.metadata.create_all(ENGINE)
                _scrub_email_from_backup_exports()
            except Exception:
                raise
        else:
            raise


def _invalidate_read_caches() -> None:
    for cache_name in (
        "_get_leaderboard_cached",
        "_get_full_leaderboard_cached",
        "_get_player_history_cached",
        "_get_session_breakdown_cached",
        "_get_stats_cached",
        "_get_perfect_score_players_cached",
    ):
        cache_fn = globals().get(cache_name)
        if cache_fn is not None and hasattr(cache_fn, "cache_clear"):
            cache_fn.cache_clear()


# ─────────────────────────────────────────────────────────────
#  CRUD HELPERS
# ─────────────────────────────────────────────────────────────
def _normalize_registration_fields(name: str, company: str) -> tuple[str, str]:
    clean_name = " ".join(name.strip().split())
    clean_company = " ".join(company.strip().split())

    if not clean_name or not clean_company:
        raise ValueError("Name and company are both required.")
    if len(clean_name) > 120 or len(clean_company) > 120:
        raise ValueError("Name and company must be 120 characters or fewer.")
    return clean_name, clean_company


def _validate_event_payload(payload: str) -> str:
    clean_payload = payload.strip()
    if not clean_payload:
        return ""
    try:
        json.loads(clean_payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Event payload must be valid JSON.") from exc
    return clean_payload


def _write_df_atomically(df: pd.DataFrame, excel_path: Path, csv_path: Path, *, sheet_name: str) -> None:
    temp_excel_path = excel_path.with_suffix(".tmp.xlsx")
    temp_csv_path = csv_path.with_suffix(".tmp.csv")
    df.to_excel(temp_excel_path, index=False, sheet_name=sheet_name)
    df.to_csv(temp_csv_path, index=False)
    os.replace(temp_excel_path, excel_path)
    os.replace(temp_csv_path, csv_path)


def _read_csv_if_exists(csv_path: Path, columns: list[str]) -> pd.DataFrame:
    if not csv_path.exists():
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in df.columns:
            df[column] = None
    return df[columns]


def _read_optional_csv(csv_path: Path, columns: list[str]) -> pd.DataFrame:
    return _read_csv_if_exists(csv_path, columns)


def _record_registration_failover(
    *,
    name: str,
    company: str,
    error: str,
    db_status: str = "failed",
) -> None:
    """Persist a registration attempt to Excel/CSV if the database write fails."""
    columns = ["recorded_at", "name", "company", "db_status", "error"]
    row = pd.DataFrame([{
        "recorded_at": _now().isoformat(),
        "name": name,
        "company": company,
        "db_status": db_status,
        "error": error[:500],
    }], columns=columns)

    with BACKUP_LOCK:
        existing = _read_csv_if_exists(REGISTRATION_FAILOVER_CSV_PATH, columns)
        updated = pd.concat([existing, row], ignore_index=True)
        _write_df_atomically(
            updated,
            REGISTRATION_FAILOVER_PATH,
            REGISTRATION_FAILOVER_CSV_PATH,
            sheet_name="failover_registrations",
        )


def record_game_session_failover(
    *,
    player_id: Optional[int],
    name: str,
    company: str,
    score: int,
    time_used: int,
    timed_out: bool,
    selections: dict[int, dict[str, Optional[bool]]],
    error: str,
    db_status: str = "failed",
) -> None:
    """Persist a game session attempt if the database write fails."""
    columns = [
        "recorded_at",
        "player_id",
        "name",
        "company",
        "score",
        "time_used",
        "timed_out",
        "is_perfect",
        "selection_count",
        "selections_json",
        "db_status",
        "error",
    ]
    row = pd.DataFrame([{
        "recorded_at": _now().isoformat(),
        "player_id": player_id,
        "name": name,
        "company": company,
        "score": score,
        "time_used": time_used,
        "timed_out": bool(timed_out),
        "is_perfect": bool(score == NUM_PAINS),
        "selection_count": len(selections or {}),
        "selections_json": json.dumps(selections, separators=(",", ":")),
        "db_status": db_status,
        "error": error[:500],
    }], columns=columns)

    with BACKUP_LOCK:
        existing = _read_csv_if_exists(GAME_SESSION_FAILOVER_CSV_PATH, columns)
        updated = pd.concat([existing, row], ignore_index=True)
        _write_df_atomically(
            updated,
            GAME_SESSION_FAILOVER_PATH,
            GAME_SESSION_FAILOVER_CSV_PATH,
            sheet_name="failover_game_sessions",
        )


def _export_registration_backup(
    *,
    force: bool = False,
    include_snapshot: bool = False,
) -> None:
    """
    Export the registration table to an Excel workbook atomically.
    This gives the event team a non-database backup they can open directly.
    """
    global _last_backup_export_at, _last_snapshot_export_at

    now = time.monotonic()
    should_write_current = force or (now - _last_backup_export_at) >= BACKUP_MIN_INTERVAL_SECONDS
    should_write_snapshot = include_snapshot and (
        force or (now - _last_snapshot_export_at) >= SNAPSHOT_MIN_INTERVAL_SECONDS
    )
    if not should_write_current and not should_write_snapshot:
        return

    with SessionFactory() as db:
        rows = db.execute(text("""
            SELECT
                id,
                name,
                company,
                created_at,
                last_seen,
                total_plays,
                best_score,
                best_time
            FROM players
            ORDER BY created_at ASC, id ASC
        """)).mappings().all()

    df = pd.DataFrame([dict(row) for row in rows])
    if df.empty:
        df = pd.DataFrame(columns=[
            "id", "name", "company", "created_at",
            "last_seen", "total_plays", "best_score", "best_time",
        ])

    with BACKUP_LOCK:
        REGISTRATION_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if should_write_current:
            _write_df_atomically(
                df,
                REGISTRATION_BACKUP_PATH,
                REGISTRATION_BACKUP_CSV_PATH,
                sheet_name="registrations",
            )
            _last_backup_export_at = time.monotonic()

        if should_write_snapshot:
            snapshot_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            snapshot_excel_path = REGISTRATION_BACKUP_DIR / f"player_registrations_{snapshot_stamp}.xlsx"
            snapshot_csv_path = REGISTRATION_BACKUP_DIR / f"player_registrations_{snapshot_stamp}.csv"
            df.to_excel(snapshot_excel_path, index=False, sheet_name="registrations")
            df.to_csv(snapshot_csv_path, index=False)
            _last_snapshot_export_at = time.monotonic()


def _export_game_sessions_backup(*, force: bool = False) -> None:
    """
    Export game sessions and selections to Excel/CSV for emergency fallback.
    This ensures data is stored outside the database on Streamlit Cloud.
    """
    global _last_game_sessions_export_at
    
    now = time.monotonic()
    if not force and (now - _last_game_sessions_export_at) < BACKUP_MIN_INTERVAL_SECONDS:
        return  # Rate-limit exports
    
    try:
        with SessionFactory() as db:
            # Export game sessions
            sessions = db.execute(text("""
                SELECT
                    gs.id AS session_id,
                    p.id AS player_id,
                    p.name,
                    p.company,
                    gs.score,
                    gs.time_used,
                    gs.timed_out,
                    gs.is_perfect,
                    gs.completed_at
                FROM game_sessions gs
                JOIN players p ON p.id = gs.player_id
                ORDER BY gs.completed_at DESC
            """)).mappings().all()
            
            sessions_df = pd.DataFrame([dict(row) for row in sessions])
            if sessions_df.empty:
                sessions_df = pd.DataFrame(columns=[
                    "session_id", "player_id", "name", "company",
                    "score", "time_used", "timed_out", "is_perfect", "completed_at"
                ])
            
            # Export selections (per-card answers)
            selections = db.execute(text("""
                SELECT
                    s.id,
                    s.session_id,
                    s.pain_idx,
                    s.owner_orig_idx,
                    s.impact_orig_idx,
                    s.owner_correct,
                    s.impact_correct,
                    s.both_correct
                FROM selections s
                ORDER BY s.session_id, s.pain_idx
            """)).mappings().all()
            
            selections_df = pd.DataFrame([dict(row) for row in selections])
            if selections_df.empty:
                selections_df = pd.DataFrame(columns=[
                    "id", "session_id", "pain_idx", "owner_orig_idx",
                    "impact_orig_idx", "owner_correct", "impact_correct", "both_correct"
                ])
    
        with BACKUP_LOCK:
            # Write sessions
            _write_df_atomically(
                sessions_df,
                GAME_SESSIONS_BACKUP_PATH,
                GAME_SESSIONS_BACKUP_CSV_PATH,
                sheet_name="sessions",
            )
            
            # Write selections
            _write_df_atomically(
                selections_df,
                SELECTIONS_BACKUP_PATH,
                SELECTIONS_BACKUP_CSV_PATH,
                sheet_name="selections",
            )
            
            _last_game_sessions_export_at = time.monotonic()
    except Exception:
        # Silently fail; backup should never block game flow
        pass


def _best_sessions_from_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "name", "company", "score", "time_used", "is_perfect",
            "timed_out", "completed_at", "session_id",
        ])

    working = df.copy()
    working["score"] = pd.to_numeric(working["score"], errors="coerce").fillna(-1)
    working["time_used"] = pd.to_numeric(working["time_used"], errors="coerce").fillna(999999)
    working["completed_at"] = pd.to_datetime(working["completed_at"], errors="coerce")
    working["is_perfect"] = working["is_perfect"].fillna(False).astype(bool)
    working["timed_out"] = working["timed_out"].fillna(False).astype(bool)
    working = working.sort_values(
        by=["score", "time_used", "completed_at"],
        ascending=[False, True, True],
        na_position="last",
    )
    return working.drop_duplicates(subset=["name", "company"], keep="first")


def _load_backup_session_rows() -> pd.DataFrame:
    backup_columns = [
        "session_id", "player_id", "name", "company", "score",
        "time_used", "timed_out", "is_perfect", "completed_at",
    ]
    failover_columns = [
        "recorded_at", "player_id", "name", "company", "score",
        "time_used", "timed_out", "is_perfect", "selection_count",
        "selections_json", "db_status", "error",
    ]

    backup_df = _read_optional_csv(GAME_SESSIONS_BACKUP_CSV_PATH, backup_columns)
    failover_df = _read_optional_csv(GAME_SESSION_FAILOVER_CSV_PATH, failover_columns)
    if not failover_df.empty:
        failover_df = failover_df.rename(columns={"recorded_at": "completed_at"})
        failover_df["session_id"] = failover_df.get("session_id")
        failover_df = failover_df[[
            "session_id", "player_id", "name", "company", "score",
            "time_used", "timed_out", "is_perfect", "completed_at",
        ]]

    combined = pd.concat([backup_df, failover_df], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(columns=backup_columns)
    return combined


def _load_backup_registration_rows() -> pd.DataFrame:
    backup_columns = [
        "id", "name", "company", "created_at", "last_seen",
        "total_plays", "best_score", "best_time",
    ]
    failover_columns = ["recorded_at", "name", "company", "db_status", "error"]

    backup_df = _read_optional_csv(REGISTRATION_BACKUP_CSV_PATH, backup_columns)
    if not backup_df.empty:
        backup_df = backup_df.rename(columns={"id": "player_id"})
        backup_df["data_source"] = "registration_backup"
        backup_df["sync_status"] = "backup_synced"
        backup_df["last_error"] = None

    failover_df = _read_optional_csv(REGISTRATION_FAILOVER_CSV_PATH, failover_columns)
    if not failover_df.empty:
        failover_df["player_id"] = None
        failover_df["created_at"] = failover_df["recorded_at"]
        failover_df["last_seen"] = failover_df["recorded_at"]
        failover_df["total_plays"] = 0
        failover_df["best_score"] = None
        failover_df["best_time"] = None
        failover_df["data_source"] = "registration_failover"
        failover_df["sync_status"] = failover_df["db_status"].fillna("failed")
        failover_df["last_error"] = failover_df["error"]
        failover_df = failover_df[[
            "player_id", "name", "company", "created_at", "last_seen",
            "total_plays", "best_score", "best_time", "data_source",
            "sync_status", "last_error",
        ]]

    empty_columns = [
        "player_id", "name", "company", "created_at", "last_seen",
        "total_plays", "best_score", "best_time", "data_source",
        "sync_status", "last_error",
    ]

    if backup_df.empty and failover_df.empty:
        return pd.DataFrame(columns=empty_columns)

    if backup_df.empty:
        combined = failover_df
    elif failover_df.empty:
        combined = backup_df[[
            "player_id", "name", "company", "created_at", "last_seen",
            "total_plays", "best_score", "best_time", "data_source",
            "sync_status", "last_error",
        ]]
    else:
        combined = pd.concat([
            backup_df[[
                "player_id", "name", "company", "created_at", "last_seen",
                "total_plays", "best_score", "best_time", "data_source",
                "sync_status", "last_error",
            ]],
            failover_df,
        ], ignore_index=True)

    combined["source_rank"] = combined["data_source"].map({
        "registration_backup": 0,
        "registration_failover": 1,
    }).fillna(9)
    combined = combined.sort_values(
        by=["source_rank", "created_at", "name", "company"],
        ascending=[True, True, True, True],
        na_position="last",
    )
    combined = combined.drop_duplicates(subset=["name", "company"], keep="first")
    return combined[[
        "player_id", "name", "company", "created_at", "last_seen",
        "total_plays", "best_score", "best_time", "data_source",
        "sync_status", "last_error",
    ]]


def _get_leaderboard_from_backups(limit: int) -> list[dict[str, Any]]:
    sessions_df = _best_sessions_from_dataframe(_load_backup_session_rows())
    if sessions_df.empty:
        return []
    rows = sessions_df[[
        "name", "company", "score", "time_used", "is_perfect", "completed_at"
    ]].head(limit).to_dict(orient="records")
    for row in rows:
        row["total_plays"] = None
    return rows


def _get_admin_panel_data_from_db() -> list[dict[str, Any]]:
    with SessionFactory() as db:
        rows = db.execute(text("""
            WITH ranked AS (
                SELECT
                    gs.id AS session_id,
                    gs.player_id,
                    gs.score,
                    gs.time_used,
                    gs.is_perfect,
                    gs.timed_out,
                    gs.completed_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY gs.player_id
                        ORDER BY gs.score DESC, gs.time_used ASC, gs.completed_at ASC
                    ) AS rn
                FROM game_sessions gs
            )
            SELECT
                p.id AS player_id,
                p.name,
                p.company,
                p.created_at,
                p.last_seen,
                p.total_plays,
                p.best_score,
                p.best_time,
                ranked.session_id AS leaderboard_session_id,
                ranked.score AS leaderboard_score,
                ranked.time_used AS leaderboard_time_used,
                ranked.is_perfect AS leaderboard_is_perfect,
                ranked.timed_out AS leaderboard_timed_out,
                ranked.completed_at AS leaderboard_completed_at,
                'database' AS data_source,
                'live_db' AS sync_status,
                NULL AS last_error
            FROM players p
            LEFT JOIN ranked
                ON ranked.player_id = p.id
               AND ranked.rn = 1
            ORDER BY
                COALESCE(ranked.score, -1) DESC,
                COALESCE(ranked.time_used, 999999) ASC,
                p.created_at ASC,
                p.id ASC
        """)).mappings().all()
        return [dict(r) for r in rows]


def _get_admin_panel_data_from_backups() -> list[dict[str, Any]]:
    registrations = _load_backup_registration_rows()
    sessions = _best_sessions_from_dataframe(_load_backup_session_rows())

    if registrations.empty and sessions.empty:
        return []

    if not sessions.empty:
        sessions = sessions.rename(columns={
            "session_id": "leaderboard_session_id",
            "score": "leaderboard_score",
            "time_used": "leaderboard_time_used",
            "is_perfect": "leaderboard_is_perfect",
            "timed_out": "leaderboard_timed_out",
            "completed_at": "leaderboard_completed_at",
        })

    merged = registrations.merge(
        sessions[[
            "name", "company", "leaderboard_session_id", "leaderboard_score",
            "leaderboard_time_used", "leaderboard_is_perfect",
            "leaderboard_timed_out", "leaderboard_completed_at",
        ]] if not sessions.empty else pd.DataFrame(columns=[
            "name", "company", "leaderboard_session_id", "leaderboard_score",
            "leaderboard_time_used", "leaderboard_is_perfect",
            "leaderboard_timed_out", "leaderboard_completed_at",
        ]),
        on=["name", "company"],
        how="outer",
    )

    if "data_source" not in merged.columns:
        merged["data_source"] = "leaderboard_backup"
    else:
        merged["data_source"] = merged["data_source"].fillna("leaderboard_backup")
    if "sync_status" not in merged.columns:
        merged["sync_status"] = "backup_only"
    else:
        merged["sync_status"] = merged["sync_status"].fillna("backup_only")
    if "last_error" not in merged.columns:
        merged["last_error"] = None

    merged["best_score"] = merged["best_score"].fillna(merged["leaderboard_score"])
    merged["best_time"] = merged["best_time"].fillna(merged["leaderboard_time_used"])
    merged["created_at"] = merged["created_at"].fillna(merged["leaderboard_completed_at"])
    merged["last_seen"] = merged["last_seen"].fillna(merged["leaderboard_completed_at"])
    merged["total_plays"] = merged["total_plays"].fillna(0)

    merged = merged.sort_values(
        by=["leaderboard_score", "leaderboard_time_used", "created_at"],
        ascending=[False, True, True],
        na_position="last",
    )
    return merged[[
        "player_id", "name", "company", "created_at", "last_seen",
        "total_plays", "best_score", "best_time", "leaderboard_session_id",
        "leaderboard_score", "leaderboard_time_used", "leaderboard_is_perfect",
        "leaderboard_timed_out", "leaderboard_completed_at", "data_source",
        "sync_status", "last_error",
    ]].to_dict(orient="records")


def upsert_player(name: str, company: str) -> tuple[Player, bool]:
    """
    Insert a new player or update last_seen if the same name/company already
    exists.  Returns (player, is_new_player).
    """
    clean_name, clean_company = _normalize_registration_fields(name, company)

    # Retry logic for transient I/O errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with SessionFactory() as db:
                player = db.scalar(
                    select(Player).where(
                        Player.name == clean_name,
                        Player.company == clean_company,
                    )
                )
                is_new = player is None

                if is_new:
                    player = Player(name=clean_name, company=clean_company)
                    db.add(player)
                else:
                    player.name = clean_name
                    player.company = clean_company
                    player.last_seen = _now()

                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    player = db.scalar(
                        select(Player).where(
                            Player.name == clean_name,
                            Player.company == clean_company,
                        )
                    )
                    if player is None:
                        raise
                    player.name = clean_name
                    player.company = clean_company
                    player.last_seen = _now()
                    db.commit()
                    is_new = False

                try:
                    _export_registration_backup(force=True, include_snapshot=True)
                except Exception as backup_exc:
                    _record_registration_failover(
                        name=clean_name,
                        company=clean_company,
                        error=f"Registration saved to database, but backup refresh failed: {backup_exc}",
                        db_status="db_saved_backup_failed",
                    )
                _invalidate_read_caches()
                return player, is_new
        except Exception as e:
            # Retry on I/O errors
            if attempt < max_retries - 1 and ("disk I/O" in str(e).lower() or "database is locked" in str(e).lower()):
                import time
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff: 0.5s, 1s, 2s
                continue
            try:
                _record_registration_failover(
                    name=clean_name,
                    company=clean_company,
                    error=str(e),
                )
            except Exception:
                pass
            raise


def log_event(player_id: Optional[int], event_type: str, payload: str = "") -> None:
    """Append a lightweight analytics event."""
    event_name = event_type.strip()
    if not event_name:
        raise ValueError("Event type is required.")
    if len(event_name) > 60:
        raise ValueError("Event type must be 60 characters or fewer.")
    clean_payload = _validate_event_payload(payload)

    with SessionFactory() as db:
        db.add(Event(player_id=player_id, event_type=event_name, payload=clean_payload))
        db.commit()
    _invalidate_read_caches()


def save_game_session(
    player_id:  int,
    score:      int,
    time_used:  int,
    timed_out:  bool,
    selections: dict[int, dict[str, Optional[bool]]],
) -> GameSession:
    """
    Persist a completed game session with per-pain selections.
    Also updates the player's aggregate stats (total_plays, best_score, best_time).

    `selections` format:
        { pain_idx: {"answer": bool | None, "is_correct": bool | None} }
    """
    if score < 0:
        raise ValueError("Score cannot be negative.")
    if time_used < 0:
        raise ValueError("Time used cannot be negative.")
    if not selections:
        raise ValueError("Selections are required.")
    for pain_idx, selection in selections.items():
        if pain_idx < 0:
            raise ValueError("Pain index cannot be negative.")
        if not isinstance(selection, dict):
            raise ValueError("Each selection must be a dictionary.")
        if "answer" not in selection:
            raise ValueError("Each selection must include an answer key.")

    # Retry logic for transient I/O errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with SessionFactory() as db:
                player = db.get(Player, player_id)
                if player is None:
                    raise ValueError(f"Unknown player id: {player_id}")

                session = GameSession(
                    player_id=player_id,
                    score=score,
                    time_used=time_used,
                    timed_out=timed_out,
                    is_perfect=(score == NUM_PAINS),
                )
                db.add(session)
                db.flush()  # get session.id before inserting children

                for pain_idx, sel in selections.items():
                    answer = sel.get("answer")
                    is_correct = bool(sel.get("is_correct"))
                    db.add(Selection(
                        session_id      = session.id,
                        pain_idx        = pain_idx,
                        owner_orig_idx  = None if answer is None else int(answer),
                        impact_orig_idx = None if answer is None else int(answer),
                        owner_correct   = is_correct,
                        impact_correct  = is_correct,
                        both_correct    = is_correct,
                    ))

                # Update player aggregate stats
                player.total_plays += 1
                player.last_seen = _now()
                if score > player.best_score or (
                    score == player.best_score and
                    (player.best_time is None or time_used < player.best_time)
                ):
                    player.best_score = score
                    player.best_time = time_used

                db.commit()
                _invalidate_read_caches()
                
                # Export to Excel as backup (don't block if it fails)
                try:
                    _export_game_sessions_backup(force=True)
                except Exception:
                    pass
                
                return session
        except Exception as e:
            # Retry on I/O errors
            if attempt < max_retries - 1 and ("disk I/O" in str(e).lower() or "database is locked" in str(e).lower()):
                import time
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff: 0.5s, 1s, 2s
                continue
            raise


# ─────────────────────────────────────────────────────────────
#  READ / QUERY HELPERS
# ─────────────────────────────────────────────────────────────
def get_leaderboard(limit: int = 20) -> list[dict[str, Any]]:
    """
    Return top `limit` unique-player best sessions, sorted by:
        1. score  DESC
        2. time   ASC  (faster is better)
        3. completed_at ASC  (earliest winner wins tiebreaker)
    One row per player (their personal best run only).
    """
    try:
        return [dict(row) for row in _get_leaderboard_cached(limit)]
    except Exception:
        return _get_leaderboard_from_backups(limit)


@lru_cache(maxsize=16)
def _get_leaderboard_cached(limit: int) -> tuple[tuple[tuple[str, Any], ...], ...]:
    with SessionFactory() as db:
        rows = db.execute(text("""
            WITH ranked AS (
                SELECT
                    gs.id          AS session_id,
                    p.name         AS name,
                    p.company      AS company,
                    gs.score       AS score,
                    gs.time_used   AS time_used,
                    gs.is_perfect  AS is_perfect,
                    gs.completed_at AS completed_at,
                    p.total_plays  AS total_plays,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.id
                        ORDER BY gs.score DESC, gs.time_used ASC, gs.completed_at ASC
                    ) AS rn
                FROM game_sessions gs
                JOIN players p ON p.id = gs.player_id
            )
            SELECT name, company, score, time_used, is_perfect,
                   total_plays, completed_at
            FROM ranked
            WHERE rn = 1
            ORDER BY score DESC, time_used ASC, completed_at ASC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()
        return tuple(tuple(dict(r).items()) for r in rows)


def get_full_leaderboard(limit: int = 100) -> list[dict[str, Any]]:
    """All sessions (not de-duplicated by player) — useful for admin view."""
    with SessionFactory() as db:
        rows = db.execute(text("""
            SELECT
                p.name, p.company,
                gs.score, gs.time_used, gs.is_perfect,
                gs.timed_out, gs.completed_at,
                gs.id AS session_id
            FROM game_sessions gs
            JOIN players p ON p.id = gs.player_id
            ORDER BY gs.score DESC, gs.time_used ASC, gs.completed_at ASC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()
        return [dict(r) for r in rows]


def get_admin_panel_data() -> list[dict[str, Any]]:
    """
    Return one row per registered player with registration details plus the
    best-run fields used by the leaderboard.
    """
    try:
        db_rows = _get_admin_panel_data_from_db()
    except Exception:
        db_rows = []

    backup_rows = _get_admin_panel_data_from_backups()
    if not db_rows:
        return backup_rows
    if not backup_rows:
        return db_rows

    def _merge_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
        session_id = row.get("leaderboard_session_id")
        if pd.isna(session_id):
            session_id = None
        return (row.get("name"), row.get("company"), session_id)

    existing_keys = {_merge_key(row) for row in db_rows}
    for row in backup_rows:
        key = _merge_key(row)
        if key not in existing_keys:
            db_rows.append(row)
    return db_rows


def get_session_breakdown(session_id: int) -> list[dict[str, Any]]:
    """Per-pain selection detail for a given session."""
    return [dict(row) for row in _get_session_breakdown_cached(session_id)]


@lru_cache(maxsize=128)
def _get_session_breakdown_cached(session_id: int) -> tuple[tuple[tuple[str, Any], ...], ...]:
    with SessionFactory() as db:
        rows = db.execute(text("""
            SELECT pain_idx, owner_orig_idx, impact_orig_idx,
                   owner_correct, impact_correct, both_correct
            FROM selections
            WHERE session_id = :sid
            ORDER BY pain_idx
        """), {"sid": session_id}).mappings().all()
        return tuple(tuple(dict(r).items()) for r in rows)


def get_stats() -> dict[str, Any]:
    """
    Aggregate stats for the register screen and admin dashboard:
     - total unique players
     - total sessions played
     - perfect scores (NUM_PAINS/NUM_PAINS) count
     - average score
     - per-pain accuracy rates
    """
    return dict(_get_stats_cached())


@lru_cache(maxsize=1)
def _get_stats_cached() -> tuple[tuple[str, Any], ...]:
    with SessionFactory() as db:
        totals = db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM players)                           AS total_players,
                (SELECT COUNT(*) FROM game_sessions)                     AS total_sessions,
                (SELECT COUNT(*) FROM game_sessions WHERE is_perfect=1)  AS perfect_count,
                (SELECT ROUND(AVG(score),2) FROM game_sessions)          AS avg_score
        """)).mappings().first()

        pain_accuracy = db.execute(text("""
            SELECT
                pain_idx,
                COUNT(*)                                AS total,
                SUM(CASE WHEN both_correct=1 THEN 1 ELSE 0 END) AS correct_count,
                ROUND(
                    100.0 * SUM(CASE WHEN both_correct=1 THEN 1 ELSE 0 END) / COUNT(*),
                    1
                ) AS accuracy_pct
            FROM selections
            GROUP BY pain_idx
            ORDER BY pain_idx
        """)).mappings().all()

        result = {
            "total_players":  totals["total_players"]  or 0,
            "total_sessions": totals["total_sessions"] or 0,
            "perfect_count":  totals["perfect_count"]  or 0,
            "avg_score":      totals["avg_score"]       or 0.0,
            "pain_accuracy":  [dict(r) for r in pain_accuracy],
        }
        return tuple(result.items())


def get_perfect_score_players() -> list[dict[str, Any]]:
    """All players who achieved at least one perfect score — for prize draw."""
    with SessionFactory() as db:
        rows = db.execute(text("""
            SELECT DISTINCT p.name, p.company,
                   MIN(gs.time_used) AS best_time,
                   MIN(gs.completed_at) AS first_perfect
            FROM game_sessions gs
            JOIN players p ON p.id = gs.player_id
            WHERE gs.is_perfect = 1
            GROUP BY p.id
            ORDER BY best_time ASC, first_perfect ASC
        """)).mappings().all()
        return [dict(r) for r in rows]


def get_registration_backup_path() -> Path:
    """Return the current Excel backup path for registration data."""
    return REGISTRATION_BACKUP_PATH


def export_admin_workbook() -> Path:
    """
    Write a persistent admin workbook with current registrations, sessions,
    and aggregate stats. The file lives in DATA_DIR so it survives app reruns.
    """
    registrations_df = pd.DataFrame(get_admin_panel_data())
    try:
        sessions_df = pd.DataFrame(get_full_leaderboard(limit=1_000_000))
    except Exception:
        sessions_df = _load_backup_session_rows()
    stats = get_stats()
    stats_df = pd.DataFrame([{
        "total_players": stats.get("total_players", 0),
        "total_sessions": stats.get("total_sessions", 0),
        "perfect_count": stats.get("perfect_count", 0),
        "avg_score": stats.get("avg_score", 0.0),
    }])
    pain_accuracy_df = pd.DataFrame(stats.get("pain_accuracy", []))

    temp_path = ADMIN_EXPORT_PATH.with_suffix(".tmp.xlsx")
    with BACKUP_LOCK:
        with pd.ExcelWriter(temp_path, engine="openpyxl") as writer:
            registrations_df.to_excel(writer, index=False, sheet_name="registrations")
            sessions_df.to_excel(writer, index=False, sheet_name="sessions")
            stats_df.to_excel(writer, index=False, sheet_name="summary")
            pain_accuracy_df.to_excel(writer, index=False, sheet_name="pain_accuracy")
        os.replace(temp_path, ADMIN_EXPORT_PATH)
    return ADMIN_EXPORT_PATH
