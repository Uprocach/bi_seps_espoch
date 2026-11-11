"""
Test Suite: Pipeline de Datos y Reemplazo Atómico Zero-Downtime (Fase 2 / SDD)
Valida contratos OpenAPI, control RBAC y conmutación de Data Marts en caliente.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.services.mart_provider import mart_provider
from backend.app.models.schemas import PipelineStatusResponse
from etl.monthly_pipeline import validate_mart_dir

client = TestClient(app)

def _auth_cookie(role: str) -> dict:
    token = create_access_token(data={"sub": f"test_{role}", "role": role})
    return {"espoch_pro_access_token": token}

def test_pipeline_status_unauthenticated_returns_401():
    """Valida que la consulta del estado del pipeline sin sesión sea rechazada con 401."""
    res = client.get("/api/v1/admin/pipeline-status")
    assert res.status_code == 401

def test_pipeline_status_investigador_forbidden_403():
    """Valida que el rol investigador no tenga privilegios para consultar el estado del pipeline."""
    cookies = _auth_cookie("investigador")
    res = client.get("/api/v1/admin/pipeline-status", cookies=cookies)
    assert res.status_code == 403

def test_pipeline_status_auditor_and_admin_allowed_200():
    """Valida que los roles auditor y administrador accedan exitosamente con HTTP 200 y formato válido."""
    for role in ["auditor", "administrador"]:
        cookies = _auth_cookie(role)
        res = client.get("/api/v1/admin/pipeline-status", cookies=cookies)
        assert res.status_code == 200
        data = res.json()
        validated = PipelineStatusResponse.model_validate(data)
        assert validated.status == "active"
        assert validated.latest_period == "2025-12"
        assert validated.periods_count >= 96
        assert validated.entities_count >= 200

def test_mart_provider_dynamic_resolution_and_atomic_switch(tmp_path):
    """Valida el mecanismo de conmutación atómica y resolución dinámica en MartPathProvider."""
    # 1. Estado inicial
    initial_status = mart_provider.get_status()
    assert initial_status["status"] == "active"

    # 2. Reemplazo atómico a 'mart' (idempotente)
    record = mart_provider.atomic_switch(new_dir_name="mart", trigger_user="test_runner")
    assert record["status"] == "success"
    assert record["switched_to"] == "mart"

    # 3. Consulta de estado post-switch
    post_status = mart_provider.get_status()
    assert post_status["last_switch_timestamp"] is not None
    assert "mart" in post_status["active_mart_dir"]

def test_pipeline_gatekeeper_validation_passes_on_production_mart():
    """Valida que el Gatekeeper de integridad matemática y referencial apruebe el Data Mart activo."""
    mart_path = mart_provider.mart_dir
    assert validate_mart_dir(mart_path) is True
