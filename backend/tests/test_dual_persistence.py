"""
Pruebas de persistencia dual (SQLite local y PostgreSQL Supabase) - ADR-0006.
"""

import tempfile
from pathlib import Path
import pytest
from backend.app.services.dual_db import DualDatabaseAdapter
from backend.app.services.user_db_service import UserDBService
from backend.app.services.audit_service import AuditService


def test_sqlite_fallback_initialization():
    """Valida que sin DATABASE_URL el servicio opere en SQLite local creando tablas y sembrando admin."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_users.db"
        service = UserDBService(db_path=test_db, database_url=None)

        assert service.is_postgres is False
        assert test_db.exists()

        # Validar siembra automática
        from backend.app.core.config import settings
        admin = service.get_user_by_username_or_email(settings.ADMIN_USER)
        assert admin is not None
        assert admin["role"] == "administrador"
        assert admin["must_change_password"] == 1


def test_postgres_url_normalization_and_routing():
    """Valida la detección y normalización de cadenas de conexión postgres:// y postgresql://."""
    url_pg = "postgres://postgres:secret@db.xyz.supabase.co:5432/postgres"
    norm = DualDatabaseAdapter.normalize_database_url(url_pg)
    assert norm == "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"

    url_std = "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"
    assert DualDatabaseAdapter.normalize_database_url(url_std) == url_std
    assert DualDatabaseAdapter.normalize_database_url(None) is None


def test_prepare_sql_conversion():
    """Valida la traducción de placeholders ? a %s según el motor de base de datos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_sql.db"
        adapter_sqlite = DualDatabaseAdapter(db_path=test_db, database_url=None)

        query = "SELECT * FROM users WHERE username = ? AND is_active = ?;"
        assert adapter_sqlite.prepare_sql(query) == query

        adapter_sqlite.is_postgres = True
        assert adapter_sqlite.prepare_sql(query) == "SELECT * FROM users WHERE username = %s AND is_active = %s;"


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

        # Insertar y listar eventos de auditoría vía AuditTrail sobre el mismo adaptador
        audit = AuditService(adapter=service.adapter)
        event = audit.log_event(
            user_sub="investigador.test",
            user_role="investigador",
            action="BENCHMARKING_COMPARE",
            resource="/api/v1/supervision/benchmarking/compare",
            details={"coops": 2},
            ip_address="127.0.0.1",
            user_agent="pytest-client"
        )
        assert event["action"] == "BENCHMARKING_COMPARE"

        logs, total = audit.query_events(user_sub="investigador.test")
        assert total >= 1
        assert logs[0]["action"] == "BENCHMARKING_COMPARE"
