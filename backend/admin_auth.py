"""Persistent account-wide admin throttling, independent of browser sessions."""
from dataclasses import dataclass
from hmac import compare_digest
import math
import time

from sqlalchemy import Column, String, Integer, Float, select
from . import database as db


class AdminThrottle(db.Base):
    __tablename__ = "admin_throttle"
    bucket = Column(String(40), primary_key=True)
    failures = Column(Integer, nullable=False, default=0)
    window_start = Column(Float, nullable=False, default=0)
    locked_until = Column(Float, nullable=False, default=0)


@dataclass(frozen=True)
class AuthResult:
    authenticated: bool = False
    configured: bool = True
    retry_after: int = 0
    message: str = "Invalid admin credentials."


def _epoch():
    return time.time()


def authenticate(username, password, configured_username, configured_password) -> AuthResult:
    if not configured_username or not configured_password:
        return AuthResult(configured=False, message="Admin access is not configured.")
    from .attempts import transaction
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    try:
        with transaction() as session:
            insert = pg_insert if db.ENGINE.dialect.name == "postgresql" else sqlite_insert
            session.execute(insert(AdminThrottle).values(bucket="admin", failures=0,
                            window_start=0, locked_until=0).on_conflict_do_nothing())
            bucket = session.scalar(select(AdminThrottle).where(
                        AdminThrottle.bucket == "admin").with_for_update())
            now = _epoch()
            if bucket.locked_until > now:
                wait = math.ceil(bucket.locked_until - now)
                return AuthResult(retry_after=wait, message=f"Too many login attempts. Try again in {wait}s.")
            if now - bucket.window_start >= 60:
                bucket.failures, bucket.window_start = 0, now
            user_ok = compare_digest(str(username).encode(), str(configured_username).encode())
            pass_ok = compare_digest(str(password).encode(), str(configured_password).encode())
            if user_ok & pass_ok:
                bucket.failures = 0
                bucket.locked_until = 0
                return AuthResult(authenticated=True, message="")
            bucket.failures += 1
            if bucket.failures >= 5:
                bucket.locked_until = now + 60
                return AuthResult(retry_after=60, message="Too many login attempts. Try again in 60s.")
            return AuthResult()
    except Exception:
        return AuthResult(message="Admin login is temporarily unavailable. Please try again.")
