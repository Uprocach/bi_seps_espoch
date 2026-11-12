import sqlite3
import hashlib
import hmac
import secrets
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
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

logger = logging.getLogger("user_db")


class UserDBService:
    """
    Servicio de gestión de usuarios y auditoría con persistencia dual:
    - PostgreSQL gestionado en Supabase cuando settings.DATABASE_URL está configurada.
    - SQLite transaccional local (data/users.db) como fallback automático para tests y desarrollo offline.
    """

    def __init__(self, db_path: Path | None = None, database_url: str | None = None):
        self.db_path = db_path or (settings.BASE_DIR / "data" / "users.db")
        raw_url = database_url or settings.DATABASE_URL
        self.database_url = self._normalize_database_url(raw_url)
        self.is_postgres = bool(
            self.database_url and (
                self.database_url.startswith("postgresql://") or 
                self.database_url.startswith("postgres://")
            )
        )

        if not self.is_postgres:
            self._ensure_db_dir()

        self._init_db()

    @staticmethod
    def _normalize_database_url(url: str | None) -> str | None:
        if not url:
            return None
        clean = url.strip()
        if clean.startswith("postgres://"):
            return "postgresql://" + clean[len("postgres://"):]
        return clean

    def _ensure_db_dir(self):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @contextmanager
    def _get_connection(self) -> Generator[Any, None, None]:
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

    def _prepare_sql(self, sql: str) -> str:
        if self.is_postgres:
            return sql.replace("?", "%s")
        return sql

    def _execute_insert(self, cursor: Any, sql_base: str, params: tuple | list) -> int:
        if self.is_postgres:
            sql = self._prepare_sql(sql_base) + " RETURNING id;"
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return row["id"] if isinstance(row, dict) else row[0]
        else:
            cursor.execute(sql_base, params)
            return cursor.lastrowid  # type: ignore

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
        if not salt:
            salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return dk.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return hmac.compare_digest(dk.hex(), hashed)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if self.is_postgres:
                # Esquema PostgreSQL (Supabase)
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
                # Esquema SQLite local con WAL mode (AUD-15)
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

            # Índices de alto rendimiento comunes a ambos motores
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_sub ON audit_logs(user_sub);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);")

            # Sembrar usuarios iniciales si la tabla users está vacía
            cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
            row = cursor.fetchone()
            count = row["cnt"] if isinstance(row, dict) else row[0]
            if count == 0:
                self._seed_default_users(cursor)

    def _seed_default_users(self, cursor: Any):
        now = datetime.now(timezone.utc).isoformat()
        seeds = [
            (
                settings.ADMIN_USER,
                getattr(settings, "ADMIN_EMAIL", "dennys.rojas@espoch.edu.ec"),
                getattr(settings, "ADMIN_FULL_NAME", "Dennys Rojas"),
                "administrador",
                settings.ADMIN_PASSWORD,
                1  # must_change_password = 1 para cambio obligatorio en primer acceso
            )
        ]

        if self.is_postgres:
            sql_seed = """
                INSERT INTO users 
                (username, email, full_name, role, password_hash, salt, is_active, must_change_password, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
                ON CONFLICT (username) DO NOTHING;
            """
        else:
            sql_seed = """
                INSERT OR IGNORE INTO users 
                (username, email, full_name, role, password_hash, salt, is_active, must_change_password, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?);
            """

        for username, email, full_name, role, pwd, must_change in seeds:
            pwd_hash, salt = self.hash_password(pwd)
            cursor.execute(sql_seed, (username, email, full_name, role, pwd_hash, salt, must_change, now))

    def get_user_by_username_or_email(self, identifier: str) -> dict | None:
        clean = identifier.strip().lower()
        sql = self._prepare_sql("""
            SELECT * FROM users 
            WHERE LOWER(username) = ? OR LOWER(email) = ?;
        """)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (clean, clean))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict | None:
        sql = self._prepare_sql("SELECT * FROM users WHERE id = ?;")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_users(self, search: str | None = None, role: str | None = None, is_active: bool | None = None) -> list[dict]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, username, email, full_name, role, is_active, must_change_password, created_at, last_login_at FROM users WHERE 1=1"
            params: list[Any] = []

            if search:
                pattern = f"%{search.strip().lower()}%"
                query += " AND (LOWER(username) LIKE ? OR LOWER(email) LIKE ? OR LOWER(full_name) LIKE ?)"
                params.extend([pattern, pattern, pattern])

            if role:
                query += " AND role = ?"
                params.append(role.strip().lower())

            if is_active is not None:
                query += " AND is_active = ?"
                params.append(1 if is_active else 0)

            query += " ORDER BY id ASC;"
            cursor.execute(self._prepare_sql(query), params)
            return [dict(row) for row in cursor.fetchall()]

    def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        role: str = "investigador",
        raw_password: str | None = None,
        must_change_password: bool = True
    ) -> dict:
        clean_user = username.strip().lower()
        clean_email = email.strip().lower()
        pwd = raw_password.strip() if raw_password and raw_password.strip() else clean_user
        pwd_hash, salt = self.hash_password(pwd)
        now = datetime.now(timezone.utc).isoformat()

        sql_base = """
            INSERT INTO users 
            (username, email, full_name, role, password_hash, salt, is_active, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """
        params = (clean_user, clean_email, full_name.strip(), role.strip().lower(), pwd_hash, salt, 1 if must_change_password else 0, now)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            user_id = self._execute_insert(cursor, sql_base, params)

        return self.get_user_by_id(user_id)  # type: ignore

    def bulk_import_users(self, items: list[dict]) -> tuple[list[dict], list[str]]:
        created: list[dict] = []
        errors: list[str] = []

        sql_base = """
            INSERT INTO users 
            (username, email, full_name, role, password_hash, salt, is_active, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()

            for idx, item in enumerate(items, start=1):
                raw_email = (item.get("email") or "").strip().lower()
                raw_user = (item.get("username") or "").strip().lower()
                full_name = (item.get("full_name") or item.get("nombre") or "").strip()
                role = (item.get("role") or item.get("rol") or "investigador").strip().lower()

                if not raw_user and raw_email:
                    raw_user = raw_email.split("@")[0]
                elif not raw_email and raw_user:
                    raw_email = f"{raw_user}@espoch.edu.ec"

                if not raw_user or not full_name:
                    errors.append(f"Fila {idx}: Falta nombre o usuario/correo.")
                    continue

                raw_pwd = (item.get("password") or item.get("clave") or raw_user).strip()
                pwd_hash, salt = self.hash_password(raw_pwd)
                params = (raw_user, raw_email, full_name, role, pwd_hash, salt, now)

                try:
                    uid = self._execute_insert(cursor, sql_base, params)
                    created.append({
                        "id": uid,
                        "username": raw_user,
                        "email": raw_email,
                        "full_name": full_name,
                        "role": role,
                        "initial_password": raw_pwd
                    })
                except (sqlite3.IntegrityError, PsycopgIntegrityError):
                    errors.append(f"Fila {idx} ({raw_user}): El usuario o correo ya está registrado.")
                    continue

        return created, errors

    def update_password(self, user_id: int, new_password: str) -> bool:
        pwd_hash, salt = self.hash_password(new_password.strip())
        sql = self._prepare_sql("""
            UPDATE users 
            SET password_hash = ?, salt = ?, must_change_password = 0 
            WHERE id = ?;
        """)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pwd_hash, salt, user_id))
            return cursor.rowcount > 0

    def reset_password(self, user_id: int, new_temp_password: str | None = None) -> tuple[bool, str]:
        user = self.get_user_by_id(user_id)
        if not user:
            return False, ""
        temp_pwd = new_temp_password.strip() if new_temp_password and new_temp_password.strip() else user["username"]
        pwd_hash, salt = self.hash_password(temp_pwd)
        sql = self._prepare_sql("""
            UPDATE users 
            SET password_hash = ?, salt = ?, must_change_password = 1 
            WHERE id = ?;
        """)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pwd_hash, salt, user_id))
            return True, temp_pwd

    def toggle_user_active(self, user_id: int, is_active: bool) -> bool:
        sql = self._prepare_sql("UPDATE users SET is_active = ? WHERE id = ?;")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (1 if is_active else 0, user_id))
            return cursor.rowcount > 0

    def record_login(self, user_id: int):
        now = datetime.now(timezone.utc).isoformat()
        sql = self._prepare_sql("UPDATE users SET last_login_at = ? WHERE id = ?;")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (now, user_id))

    def insert_audit_log(
        self,
        timestamp: str,
        user_sub: str,
        user_role: str,
        action: str,
        resource: str,
        details_json: str = "{}",
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> int:
        sql_base = """
            INSERT INTO audit_logs 
            (timestamp, user_sub, user_role, action, resource, details_json, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (timestamp, user_sub, user_role, action, resource, details_json, ip_address, user_agent)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            log_id = self._execute_insert(cursor, sql_base, params)
            return log_id

    def list_audit_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        user_sub: str | None = None,
        action: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> tuple[list[dict], int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            where_clauses = ["1=1"]
            params: list[Any] = []

            if user_sub:
                where_clauses.append("LOWER(user_sub) LIKE ?")
                params.append(f"%{user_sub.strip().lower()}%")

            if action:
                where_clauses.append("action = ?")
                params.append(action.strip())

            if start_date:
                where_clauses.append("timestamp >= ?")
                params.append(start_date.strip())

            if end_date:
                val = end_date.strip()
                if len(val) == 10:
                    val += "T23:59:59"
                where_clauses.append("timestamp <= ?")
                params.append(val)

            where_str = " AND ".join(where_clauses)

            # Contar total de registros filtrados
            count_sql = self._prepare_sql(f"SELECT COUNT(*) AS cnt FROM audit_logs WHERE {where_str};")
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total = row["cnt"] if isinstance(row, dict) else row[0]

            # Consultar página con orden cronológico descendente
            query = f"""
                SELECT id, timestamp, user_sub, user_role, action, resource, details_json, ip_address, user_agent
                FROM audit_logs
                WHERE {where_str}
                ORDER BY id DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(self._prepare_sql(query), params + [limit, offset])
            rows = cursor.fetchall()
            return [dict(r) for r in rows], total


user_db = UserDBService()
