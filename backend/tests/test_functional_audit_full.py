import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)

def test_audit_mp01_metadata_filters():
    """Modo Público: GET /api/v1/indicators/metadata y /api/v1/metadata/filters."""
    res1 = client.get("/api/v1/indicators/metadata")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "indicators" in data1
    assert "periods" in data1
    assert "segments" in data1
    assert "provinces" in data1

    res2 = client.get("/api/v1/metadata/filters")
    assert res2.status_code == 200
    assert len(res2.json()["indicators"]) >= 23

def test_audit_mp02_entities_directory():
    """Modo Público: GET /api/v1/entities?page=1&page_size=10."""
    res = client.get("/api/v1/entities?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) == 10
    assert data["pagination"]["total_items"] > 200

def test_audit_mp03_country_series():
    """Modo Público: GET /api/v1/indicators/series?indicator=roa&level=country."""
    res = client.get("/api/v1/indicators/series?indicator=roa&level=country")
    assert res.status_code == 200
    data = res.json()
    assert len(data["series"]) == 1
    assert len(data["series"][0]["points"]) > 0

def test_audit_mp04_segment_series_normalized():
    """Modo Público: GET /api/v1/indicators/series?indicator=roa&level=segment&segment=1."""
    res = client.get("/api/v1/indicators/series?indicator=roa&level=segment&segment=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["series"]) == 1
    assert data["series"][0]["key"] == "SEGMENTO_1"
    assert len(data["series"][0]["points"]) > 0

def test_audit_mp05_entity_public_unauthenticated():
    """Modo Público: GET /api/v1/indicators/series?indicator=roa&level=entity&ruc=0190155722001 (debe responder 200 sin sesión)."""
    res = client.get("/api/v1/indicators/series?indicator=roa&level=entity&ruc=0190155722001")
    assert res.status_code == 200
    data = res.json()
    assert len(data["series"]) == 1
    assert data["series"][0]["key"] == "0190155722001"
    assert "JARDIN AZUAYO" in data["series"][0]["label"]

def test_audit_mp06_public_benchmark_matrix_blocked_403():
    """Modo Público: Intento de acceso público a /api/v1/indicators/benchmark-matrix debe responder 403 Forbidden."""
    res = client.get("/api/v1/indicators/benchmark-matrix")
    assert res.status_code == 403
    assert "credenciales institucionales" in res.json()["detail"].lower()

def test_audit_mp07_public_pro_compare_blocked_401():
    """Modo Público: Intento de acceso público a /api/v1/pro/compare debe responder 401 Unauthorized."""
    res = client.get("/api/v1/pro/compare")
    assert res.status_code == 401

def test_audit_mp08_public_audit_logs_blocked_401():
    """Modo Público: Intento de acceso público a /api/v1/admin/audit-logs debe responder 401 Unauthorized."""
    res = client.get("/api/v1/admin/audit-logs")
    assert res.status_code == 401

def test_audit_ma01_auth_token_and_cookie_injection():
    """Modo Acreditado: Autenticación POST /api/v1/auth/token e inyección de cookie HttpOnly."""
    login_payload = {
        "username": "investigador.espoch",
        "password": "EspochPro2026#",
        "role": "investigador"
    }
    res = client.post("/api/v1/auth/token", json=login_payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "investigador"

    # Verificar presencia de la cookie en el cliente
    set_cookie = res.headers.get("set-cookie", "")
    assert settings.COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie

def test_audit_ma02_accredited_pro_compare_5_entities_camel():
    """Modo Acreditado: Acceso a /api/v1/pro/compare con hasta 5 cooperativas y semáforos CAMEL."""
    # Autenticar primero
    client.post("/api/v1/auth/login", json={
        "username": "investigador.espoch",
        "password": "EspochPro2026#",
        "role": "investigador"
    })
    
    rucs = "0190155722001,1790016919001,0590040718001,0190097510001,1890001041001"
    res = client.get(f"/api/v1/pro/compare?rucs={rucs}")
    assert res.status_code == 200
    comp_data = res.json()
    assert len(comp_data["entities"]) == 5
    assert len(comp_data["indicators"]) > 0

    # Verificar que los semáforos CAMEL están evaluados
    assert any(ind["segment1_baseline"] is not None for ind in comp_data["indicators"])
    for ind in comp_data["indicators"]:
        for ent in comp_data["entities"]:
            ruc_val = ent["ruc"]
            ev = ind["entity_evaluations"].get(ruc_val)
            if ev:
                assert ev["status"] in ["GREEN", "YELLOW", "RED"]
                assert ev["message"] != ""

def test_audit_ma03_accredited_benchmark_matrix():
    """Modo Acreditado: Acceso acreditado a /api/v1/indicators/benchmark-matrix."""
    client.post("/api/v1/auth/login", json={
        "username": "investigador.espoch",
        "password": "EspochPro2026#",
        "role": "investigador"
    })
    res = client.get("/api/v1/indicators/benchmark-matrix?ruc=0190155722001&ruc=1790016919001&period=2025-12")
    assert res.status_code == 200
    mat = res.json()
    assert "matrix" in mat
    assert len(mat["matrix"]) >= 8
    assert res.headers.get("Cache-Control") == "public, max-age=86400"
    assert res.headers.get("ETag") is not None

def test_audit_ga01_admin_audit_logs_and_filters():
    """Gobernanza: Consulta de eventos forenses GET /api/v1/admin/audit-logs con usuario auditor/admin."""
    client.post("/api/v1/auth/login", json={
        "username": "auditor.espoch",
        "password": "EspochAuditor2026#",
        "role": "auditor"
    })
    res = client.get("/api/v1/admin/audit-logs?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "logs" in data
    assert "total" in data
    assert data["total"] > 0
    assert len(data["logs"]) > 0

def test_audit_ga02_sqlite_wal_mode_and_audit_structure():
    """Gobernanza: Comprobar que en data/users.db los logs se insertan en WAL mode y persisten con la estructura forense."""
    db_path = Path("data/users.db")
    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    j_mode = cursor.fetchone()[0]
    assert j_mode.lower() == "wal"

    cursor.execute("PRAGMA table_info(audit_logs);")
    cols = {row[1] for row in cursor.fetchall()}
    assert {"id", "timestamp", "user_sub", "user_role", "action", "resource", "details_json", "ip_address"}.issubset(cols)

    cursor.execute("SELECT COUNT(*) FROM audit_logs;")
    count = cursor.fetchone()[0]
    assert count > 0
    conn.close()
