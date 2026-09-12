"""Server configuration without a Streamlit dependency or secret logging."""
import os
import tomllib
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def secrets() -> dict:
    path = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as source:
            return tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError):
        raise ValueError("Cannot read application secrets. Check TOML configuration.") from None


def setting(name: str, default: str = "") -> str:
    return str(os.environ[name] if name in os.environ else secrets().get(name, default))


def database_url() -> str:
    # An explicit empty override is the isolated-test/local SQLite switch.
    return os.environ.get("CLOUD_CHAOS_DATABASE_URL", setting("DATABASE_URL")).strip()
