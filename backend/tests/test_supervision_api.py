"""
Pruebas de verificación de los endpoints de Supervisión Institucional Acreditada (Ticket 02)
Valida RBAC, benchmarking CAMEL, exportación en streaming y auditoría forense bajo /api/v1/supervision.
"""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import create_access_token

def test_supervision_compare_unauthenticated_returns_401():
    client = TestClient(app)
    res = client.post("/api/v1/supervision/benchmarking/compare", json={
        "entity_ids": ["0190155722001"],
        "start_date": "2024-01",
        "end_date": "2025-12"
    })
    assert res.status_code == 401

def test_supervision_compare_accredited_returns_200():
    client = TestClient(app)
    token = create_access_token({"sub": "investigador.espoch", "role": "investigador"})
    client.cookies.set(settings.COOKIE_NAME, token)

    res = client.post("/api/v1/supervision/benchmarking/compare", json={
        "entity_ids": ["0190155722001", "0190115798001"],
        "start_date": "2024-01",
        "end_date": "2025-12"
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["entities"]) == 2
    assert "indicators" in data
    assert len(data["indicators"]) > 0

def test_supervision_export_csv_accredited_returns_200():
    client = TestClient(app)
    token = create_access_token({"sub": "investigador.espoch", "role": "investigador"})
    client.cookies.set(settings.COOKIE_NAME, token)

    res = client.post("/api/v1/supervision/export/csv", json={
        "entity_ids": ["0190155722001"],
        "start_date": "2025-01",
        "end_date": "2025-03"
    })
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "0190155722001" in res.text

def test_supervision_export_excel_auditor_returns_200():
    client = TestClient(app)
    token = create_access_token({"sub": "auditor.espoch", "role": "auditor"})
    client.cookies.set(settings.COOKIE_NAME, token)

    res = client.post("/api/v1/supervision/export/excel", json={
        "entity_ids": ["0190155722001"],
        "start_date": "2025-01",
        "end_date": "2025-03"
    })
    assert res.status_code == 200
    assert "spreadsheetml.sheet" in res.headers["content-type"]
    assert res.content.startswith(b"PK\x03\x04")
