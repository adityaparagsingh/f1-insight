"""F1 INSIGHT application configuration.

Loads environment variables from the project-root `.env` file (falling back
to process environment).  No credentials are ever hard-coded in source.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Project root = <root>/f1-insight
BACKEND_DIR = Path(__file__).resolve().parents[1]      # .../f1-insight/backend
PROJECT_ROOT = BACKEND_DIR.parent                      # .../f1-insight

# Load .env from project root (and allow overrides from the real environment)
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")  # optional backend-local .env


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://f1user:f1pass@127.0.0.1:3306/f1_insight",
)

JOLPICA_BASE_URL: str = os.getenv("JOLPICA_BASE_URL", "https://api.jolpi.ca/ergast/f1").rstrip("/")
JOLPICA_TIMEOUT: int = _int("JOLPICA_TIMEOUT", 30)
JOLPICA_MAX_RETRIES: int = _int("JOLPICA_MAX_RETRIES", 5)
JOLPICA_REQUESTS_PER_SECOND: float = _float("JOLPICA_REQUESTS_PER_SECOND", 8.0)

ETL_CACHE_DIR: Path = Path(os.getenv("ETL_CACHE_DIR", str(BACKEND_DIR / "etl" / "cache")))
ETL_LOG_DIR: Path = Path(os.getenv("ETL_LOG_DIR", str(BACKEND_DIR / "logs")))

API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
API_PORT: int = _int("API_PORT", 8000)
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


@lru_cache(maxsize=1)
def get_database_url() -> str:
    return DATABASE_URL
