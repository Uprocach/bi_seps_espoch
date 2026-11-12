"""
Pruebas de persistencia dual (SQLite local y PostgreSQL Supabase) - ADR-0006.
"""

import tempfile
from pathlib import Path
import pytest
from backend.app.services.user_db_service import UserDBService


def test_sqlite_fallback_initialization():
    """Valida que sin DATABASE_URL el servicio opere en SQLite local creando tablas y sembrando admin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_users.db"
        service = UserDBService(db_path=test_db, database_url=None)

        assert service.is_postgres is False
        assert test_db.exists()

        # Validar siembra automática
        admin = service.get_user_by_username_or_email("admin.espoch")
        assert admin is not None
        assert admin["role"] == "administrador"
        assert admin["must_change_password"] == 0


def test_postgres_url_normalization_and_routing():
    """Valida la detección y normalización de cadenas de conexión postgres:// y postgresql://."""
    service_pg = UserDBService.__new__(UserDBService)
    url_pg = "postgres://postgres:secret@db.xyz.supabase.co:5432/postgres"
    norm = service_pg._normalize_database_url(url_pg)
    assert norm == "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"

    url_std = "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"
    assert service_pg._normalize_database_url(url_std) == url_std
    assert service_pg._normalize_database_url(None) is None


def test_prepare_sql_conversion():
    """Valida la traducción de placeholders ? a %s según el motor de base de datos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_sql.db"
        service_sqlite = UserDBService(db_path=test_db, database_url=None)

        query = "SELECT * FROM users WHERE username = ? AND is_active = ?;"
        assert service_sqlite._prepare_sql(query) == query

        service_sqlite.is_postgres = True
        assert service_sqlite._prepare_sql(query) == "SELECT * FROM users WHERE username = %s AND is_active = %s;"


def test_dual_service_crud_cycle_sqlite():
    """Valida el ciclo completo de creación, auditoría y modificación en base de datos aislada."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "crud_test.db"
        service = UserDBService(db_path=test_db)

        # Crear usuario
        user = service.create_user(
            username="investigador.test",
            email="investigador.test@espoch.edu.ec",
            full_name="Investigador de Prueba",
            role="investigador",
            raw_password="TestPassword123#",
            must_change_password=True
        )
        assert user["id"] is not None
        assert user["username"] == "investigador.test"

        # Verificar password
        assert service.verify_password("TestPassword123#", user["password_hash"], user["salt"]) is True
        assert service.verify_password("WrongPassword", user["password_hash"], user["salt"]) is False

        # Actualizar password
        updated = service.update_password(user["id"], "NewSecurePassword456#")
        assert updated is True

        user_updated = service.get_user_by_id(user["id"])
        assert user_updated["must_change_password"] == 0
        assert service.verify_password("NewSecurePassword456#", user_updated["password_hash"], user_updated["salt"]) is True

        # Toggle activo
        service.toggle_user_active(user["id"], False)
        user_inactive = service.get_user_by_id(user["id"])
        assert user_inactive["is_active"] == 0

        # Insertar y listar logs de auditoría
        log_id = service.insert_audit_log(
            timestamp="2026-11-12T10:00:00Z",
            user_sub="investigador.test",
            user_role="investigador",
            action="BENCHMARKING_COMPARE",
            resource="/api/v1/supervision/benchmarking/compare",
            details_json='{"coops": 2}',
            ip_address="127.0.0.1",
            user_agent="pytest-client"
        )
        assert log_id is not None

        logs, total = service.list_audit_logs(user_sub="investigador.test")
        assert total >= 1
        assert logs[0]["action"] == "BENCHMARKING_COMPARE"
