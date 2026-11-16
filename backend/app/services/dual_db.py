"""
Adaptador de Persistencia Dual (ADR-0006):
Encapsula la conexión transaccional, traducción de dialecto SQL (? -> %s),
inserción con retorno de ID e inicialización idempotente de esquema entre
PostgreSQL (Supabase) y SQLite local con modo WAL.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg import IntegrityError as PsycopgIntegrityError
except ImportError:
    psycopg = None  # type: ignore
    dict_row = None  # type: ignore
    PsycopgIntegrityError = sqlite3.IntegrityError  # type: ignore

from backend.app.core.config import settings


class DualDatabaseAdapter:
    """Costura única `local-substitutable` entre PostgreSQL (producción) y SQLite (local/tests)."""

    integrity_errors: tuple[type[BaseException], ...] = (
        sqlite3.IntegrityError,
        PsycopgIntegrityError,
    )

    def __init__(self, db_path: Path | None = None, database_url: str | None = None):
        self.db_path = db_path or (settings.BASE_DIR / "data" / "users.db")
        raw_url = database_url if database_url is not None else settings.DATABASE_URL
        self.database_url = self.normalize_database_url(raw_url)
        self.is_postgres = bool(
            self.database_url
            and (
                self.database_url.startswith("postgresql://")
                or self.database_url.startswith("postgres://")
            )
        )

        if not self.is_postgres:
            self._ensure_db_dir()

        self._init_schema()

    @staticmethod
    def normalize_database_url(url: str | None) -> str | None:
        if not url:
            return None
        clean = url.strip()
        if clean.startswith("postgres://"):
            return "postgresql://" + clean[len("postgres://"):]
        return clean

    def _ensure_db_dir(self) -> None:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @contextmanager
    def connection(self) -> Generator[Any, None, None]:
        if self.is_postgres:
            if not psycopg:
                raise RuntimeError("El paquete psycopg no está instalado para conexión PostgreSQL.")
            conn = psycopg.connect(self.database_url, row_factory=dict_row)
            try:
                with conn:
                    yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(str(self.db_path), timeout=15.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout = 5000;")
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def prepare_sql(self, sql: str) -> str:
        if self.is_postgres:
            return sql.replace("?", "%s")
        return sql

    def execute_insert(self, cursor: Any, sql_base: str, params: tuple | list) -> int:
        if self.is_postgres:
            sql = self.prepare_sql(sql_base) + " RETURNING id;"
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return row["id"] if isinstance(row, dict) else row[0]
        cursor.execute(sql_base, params)
        return cursor.lastrowid  # type: ignore

    def _init_schema(self) -> None:
        with self.connection() as conn:
            cursor = conn.cursor()

            if self.is_postgres:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        full_name TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'investigador',
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        must_change_password INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        last_login_at TEXT
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id SERIAL PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        user_sub TEXT NOT NULL,
                        user_role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource TEXT NOT NULL,
                        details_json TEXT NOT NULL DEFAULT '{}',
                        ip_address TEXT,
                        user_agent TEXT
                    );
                """)
            else:
                cursor.execute("PRAGMA journal_mode = WAL;")
                cursor.execute("PRAGMA synchronous = NORMAL;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        full_name TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'investigador',
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        must_change_password INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        last_login_at TEXT
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_sub TEXT NOT NULL,
                        user_role TEXT NOT NULL,
                        action TEXT NOT NULL,
                        resource TEXT NOT NULL,
                        details_json TEXT NOT NULL DEFAULT '{}',
                        ip_address TEXT,
                        user_agent TEXT
                    );
                """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_sub ON audit_logs(user_sub);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);")


dual_db = DualDatabaseAdapter()
