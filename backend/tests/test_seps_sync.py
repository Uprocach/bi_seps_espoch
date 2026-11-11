"""
Test Suite: Sincronización Web Automatizada SEPS y Orquestación de Pipeline (Fase 3 / SDD)
Valida contratos OpenAPI, control de acceso RBAC, crawler web y tareas en segundo plano.
"""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token
from backend.app.models.schemas import PipelineSyncStatusResponse
from backend.app.services.sync_manager import sync_manager

client = TestClient(app)

def _auth_cookie(role: str) -> dict:
    token = create_access_token(data={"sub": f"test_{role}", "role": role})
    return {"espoch_pro_access_token": token}

def test_pipeline_sync_status_unauthenticated_returns_401():
    """Valida que la consulta de estado de sincronización sin credenciales retorne 401 Unauthorized."""
    res = client.get("/api/v1/admin/pipeline-sync-status")
    assert res.status_code == 401

def test_pipeline_sync_status_investigador_forbidden_403():
    """Valida que el rol investigador no tenga privilegios para consultar el estado de sincronización."""
    cookies = _auth_cookie("investigador")
    res = client.get("/api/v1/admin/pipeline-sync-status", cookies=cookies)
    assert res.status_code == 403

def test_pipeline_sync_status_auditor_and_admin_allowed_200():
    """Valida que roles auditor y administrador puedan consultar el estado con formato Pydantic válido."""
    for role in ["auditor", "administrador"]:
        cookies = _auth_cookie(role)
        res = client.get("/api/v1/admin/pipeline-sync-status", cookies=cookies)
        assert res.status_code == 200
        data = res.json()
        validated = PipelineSyncStatusResponse.model_validate(data)
        assert validated.status in ["idle", "downloading", "extracting", "validating", "success", "failed"]
        assert 0 <= validated.progress_percent <= 100
        assert validated.message is not None

def test_pipeline_sync_trigger_non_admin_forbidden_403():
    """Valida que solo el rol administrador pueda disparar la sincronización web."""
    for role in ["investigador", "auditor"]:
        cookies = _auth_cookie(role)
        res = client.post("/api/v1/admin/pipeline-sync", json={"force": False}, cookies=cookies)
        assert res.status_code == 403

def test_pipeline_sync_dry_run_admin_allowed_200():
    """Valida que el modo simulación (dry-run) responda HTTP 200 con el periodo detectado."""
    cookies = _auth_cookie("administrador")
    mock_catalog = {
        "eeff_mensuales_bases": {2026: 3258},
        "patrimonio_tecnico": {2026: 3250},
        "latest_year_available": 2026,
        "total_links_found": 184
    }
    with patch("etl.seps_crawler.seps_crawler.discover_downloads", return_value=mock_catalog):
        res = client.post("/api/v1/admin/pipeline-sync", json={"dry_run": True}, cookies=cookies)
        assert res.status_code == 200
        data = res.json()
        validated = PipelineSyncStatusResponse.model_validate(data)
        assert "2026" in validated.message
        assert validated.detected_period == "2026-08"

def test_pipeline_sync_trigger_accepted_202():
    """Valida que una petición válida de sincronización sea aceptada de inmediato con HTTP 202."""
    cookies = _auth_cookie("administrador")
    with patch.object(sync_manager, "run_sync_task", return_value=None):
        res = client.post("/api/v1/admin/pipeline-sync", json={"force": False, "dry_run": False}, cookies=cookies)
        assert res.status_code == 202
        data = res.json()
        validated = PipelineSyncStatusResponse.model_validate(data)
        assert validated.status == "downloading"
        assert validated.progress_percent == 10

def test_seps_crawler_discover_logic():
    """Valida la lógica de descubrimiento y categorización del crawler SEPS."""
    from etl.seps_crawler import SepsCrawler
    crawler = SepsCrawler()
    
    mock_html = """
    <div>
      <h3>Estados Financieros Mensuales</h3>
      <p>Bases de Datos:</p>
      <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&amp;download_id=9999">2026</a>
      <h3>Patrimonio técnico</h3>
      <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&amp;download_id=8888">2026</a>
    </div>
    """
    with patch.object(crawler, "fetch_portal_html", return_value=mock_html):
        cat = crawler.discover_downloads()
        assert cat["latest_year_available"] == 2026
        assert cat["eeff_mensuales_bases"][2026] == 9999
        assert cat["patrimonio_tecnico"][2026] == 8888
