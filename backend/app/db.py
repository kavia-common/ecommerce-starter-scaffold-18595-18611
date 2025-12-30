import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple

import psycopg2
import psycopg2.extras


@dataclass(frozen=True)
class DbConfig:
    """PostgreSQL connection config parsed from db_connection.txt."""
    dsn: str


def _resolve_db_connection_file() -> str:
    """
    Resolve the path to the shared db_connection.txt file created in the database container workspace.

    This scaffold places containers as sibling folders under `ecommerce-starter-scaffold-*`.
    Backend container:   ecommerce-starter-scaffold-*/backend/...
    Database container:  ecommerce-starter-scaffold-*/database/db_connection.txt
    """
    here = os.path.dirname(os.path.abspath(__file__))
    # here: .../backend/app
    backend_root = os.path.abspath(os.path.join(here, ".."))  # .../backend
    project_root = os.path.abspath(os.path.join(backend_root, ".."))  # .../ecommerce-starter-scaffold-*
    candidate = os.path.join(project_root, "database", "db_connection.txt")
    return candidate


def load_db_config() -> DbConfig:
    """
    Load database connection config from db_connection.txt.

    Expected format (per scaffold conventions):
      psql postgresql://user:pass@host:port/dbname

    Raises:
      RuntimeError if file is missing or cannot be parsed.
    """
    path = _resolve_db_connection_file()
    if not os.path.exists(path):
        raise RuntimeError(
            f"db_connection.txt not found at expected path: {path}. "
            "This backend expects the database container workspace to be present as a sibling directory."
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    # allow plain postgresql://... or "psql postgresql://..."
    match = re.search(r"(postgresql://\S+)", raw)
    if not match:
        raise RuntimeError(f"Unable to parse PostgreSQL DSN from db_connection.txt content: {raw!r}")

    dsn = match.group(1)
    return DbConfig(dsn=dsn)


@contextmanager
def get_conn() -> Iterator["psycopg2.extensions.connection"]:
    """
    Context manager that yields a psycopg2 connection with dict-row cursor support.

    Ensures connection is closed and commits/rollbacks properly.
    """
    cfg = load_db_config()
    conn = psycopg2.connect(cfg.dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
    """Run a SELECT query and return rows as list of dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
            return [dict(r) for r in rows]


def fetch_one(sql: str, params: Optional[Tuple[Any, ...]] = None) -> Optional[Dict[str, Any]]:
    """Run a SELECT query and return a single row as dict (or None)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
            return dict(row) if row else None


def execute(sql: str, params: Optional[Tuple[Any, ...]] = None) -> int:
    """
    Execute a non-SELECT statement.

    Returns:
      rowcount from cursor.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount
