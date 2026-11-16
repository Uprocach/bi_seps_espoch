import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.services.audit_service import audit_service

client = TestClient(app)

def test_audit_logs_unauthenticated_returns_401():
    response = client.get("/api/v1/admin/audit-logs")
    assert response.status_code == 401

def test_audit_logs_investigador_forbidden_403():
    token = create_access_token({"sub": "investigador.espoch", "role": "investigador"})
    response = client.get(
        "/api/v1/admin/audit-logs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "no cuenta con permisos suficientes" in response.json()["detail"]

def test_audit_logs_auditor_allowed_200():
    # Registrar evento de prueba
    audit_service.log_event(
        user_sub="test_auditor_user",
        user_role="auditor",
        action="test:audit_query_action",
        resource="/api/v1/pro/benchmarking",
        details={"audit_test": True}
    )

    token = create_access_token({"sub": "auditor.espoch", "role": "auditor"})
    response = client.get(
        "/api/v1/admin/audit-logs?action=test:audit_query_action",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any(log["user_sub"] == "test_auditor_user" for log in data["logs"])

def test_audit_logs_admin_allowed_and_filters():
    token = create_access_token({"sub": "admin.espoch", "role": "administrador"})
    response = client.get(
        "/api/v1/admin/audit-logs?limit=10&offset=0",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert isinstance(data["logs"], list)


def test_mart_atomic_switch_persists_pipeline_switch_audit_event(tmp_path, monkeypatch):
    """Regresión: atomic_switch debe registrar pipeline:switch en AuditTrail."""
    from backend.app.core.config import settings
    from backend.app.services.dual_db import DualDatabaseAdapter
    from backend.app.services.audit_service import AuditService
    import backend.app.services.audit_service as audit_mod
    from backend.app.services.mart_provider import MartPathProvider

    processed_dir = tmp_path / "processed"
    mart_dir = processed_dir / "mart"
    staging_dir = processed_dir / "mart_staging"
    mart_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    monkeypatch.setattr(settings, "DATA_MART_DIR", mart_dir)

    isolated_audit = AuditService(
        adapter=DualDatabaseAdapter(db_path=tmp_path / "audit_switch.db", database_url=None)
    )
    monkeypatch.setattr(audit_mod, "audit_service", isolated_audit)

    provider = MartPathProvider()
    record = provider.atomic_switch(new_dir_name="mart_staging", trigger_user="admin.test", validate=False)

    assert record["switched_to"] == "mart_staging"
    events, total = isolated_audit.query_events(action="pipeline:switch", user_sub="admin.test")
    assert total == 1
    assert events[0]["action"] == "pipeline:switch"
    assert events[0]["resource"] == "/api/v1/admin/pipeline/switch"
