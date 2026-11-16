import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.services.dual_db import DualDatabaseAdapter, dual_db

logger = logging.getLogger("user_db")


class UserDBService:
    """
    Repositorio de usuarios acreditados y credenciales (PBKDF2-HMAC-SHA256),
    respaldado por la costura DualDatabaseAdapter (PostgreSQL Supabase o SQLite local).
    """

    def __init__(
        self,
        db_path: Path | None = None,
        database_url: str | None = None,
        adapter: DualDatabaseAdapter | None = None,
    ):
        if adapter is not None:
            self.adapter = adapter
        elif db_path is not None or database_url is not None:
            self.adapter = DualDatabaseAdapter(db_path=db_path, database_url=database_url)
        else:
            self.adapter = dual_db

        self._ensure_default_admin()

    @property
    def is_postgres(self) -> bool:
        return self.adapter.is_postgres

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

    def _ensure_default_admin(self) -> None:
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
            row = cursor.fetchone()
            count = row["cnt"] if isinstance(row, dict) else row[0]
            if count == 0:
                self._seed_default_users(cursor)

    def _seed_default_users(self, cursor: Any) -> None:
        now = datetime.now(timezone.utc).isoformat()
        seeds = [
            (
                settings.ADMIN_USER,
                getattr(settings, "ADMIN_EMAIL", "dennys.rojas@espoch.edu.ec"),
                getattr(settings, "ADMIN_FULL_NAME", "Dennys Rojas"),
                "administrador",
                settings.ADMIN_PASSWORD,
                1,
            )
        ]

        if self.adapter.is_postgres:
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
        sql = self.adapter.prepare_sql("""
            SELECT * FROM users
            WHERE LOWER(username) = ? OR LOWER(email) = ?;
        """)
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (clean, clean))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict | None:
        sql = self.adapter.prepare_sql("SELECT * FROM users WHERE id = ?;")
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_users(self, search: str | None = None, role: str | None = None, is_active: bool | None = None) -> list[dict]:
        with self.adapter.connection() as conn:
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
            cursor.execute(self.adapter.prepare_sql(query), params)
            return [dict(row) for row in cursor.fetchall()]

    def create_user(
        self,
        username: str,
        email: str,
        full_name: str,
        role: str = "investigador",
        raw_password: str | None = None,
        must_change_password: bool = True,
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
        params = (
            clean_user,
            clean_email,
            full_name.strip(),
            role.strip().lower(),
            pwd_hash,
            salt,
            1 if must_change_password else 0,
            now,
        )

        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            user_id = self.adapter.execute_insert(cursor, sql_base, params)

        return self.get_user_by_id(user_id)  # type: ignore

    def bulk_import_users(self, items: list[dict]) -> tuple[list[dict], list[str]]:
        created: list[dict] = []
        errors: list[str] = []

        sql_base = """
            INSERT INTO users
            (username, email, full_name, role, password_hash, salt, is_active, must_change_password, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
        """

        with self.adapter.connection() as conn:
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
                    uid = self.adapter.execute_insert(cursor, sql_base, params)
                    created.append({
                        "id": uid,
                        "username": raw_user,
                        "email": raw_email,
                        "full_name": full_name,
                        "role": role,
                        "initial_password": raw_pwd,
                    })
                except self.adapter.integrity_errors:
                    errors.append(f"Fila {idx} ({raw_user}): El usuario o correo ya está registrado.")
                    continue

        return created, errors

    def update_password(self, user_id: int, new_password: str) -> bool:
        pwd_hash, salt = self.hash_password(new_password.strip())
        sql = self.adapter.prepare_sql("""
            UPDATE users
            SET password_hash = ?, salt = ?, must_change_password = 0
            WHERE id = ?;
        """)
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pwd_hash, salt, user_id))
            return cursor.rowcount > 0

    def reset_password(self, user_id: int, new_temp_password: str | None = None) -> tuple[bool, str]:
        user = self.get_user_by_id(user_id)
        if not user:
            return False, ""
        temp_pwd = new_temp_password.strip() if new_temp_password and new_temp_password.strip() else user["username"]
        pwd_hash, salt = self.hash_password(temp_pwd)
        sql = self.adapter.prepare_sql("""
            UPDATE users
            SET password_hash = ?, salt = ?, must_change_password = 1
            WHERE id = ?;
        """)
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (pwd_hash, salt, user_id))
            return True, temp_pwd

    def toggle_user_active(self, user_id: int, is_active: bool) -> bool:
        sql = self.adapter.prepare_sql("UPDATE users SET is_active = ? WHERE id = ?;")
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (1 if is_active else 0, user_id))
            return cursor.rowcount > 0

    def record_login(self, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        sql = self.adapter.prepare_sql("UPDATE users SET last_login_at = ? WHERE id = ?;")
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (now, user_id))


UserRepository = UserDBService
user_db = UserDBService(adapter=dual_db)
