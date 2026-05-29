import os
from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

import src.utils as utils


def _db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable not set")
    return url


@contextmanager
def _cursor() -> Generator[psycopg2.extensions.cursor, None, None]:
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_many(sql: str, values: list[tuple]) -> utils.Result[int]:
    try:
        with _cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, values)
        return utils.ok(len(values))
    except Exception as e:
        return utils.err(RuntimeError(str(e)), "Database upsert failed")


def fetch_all(sql: str, params: tuple = ()) -> utils.Result[list[dict]]:
    try:
        with _cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return utils.ok([dict(r) for r in rows])
    except Exception as e:
        return utils.err(RuntimeError(str(e)), "Database query failed")
