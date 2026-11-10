import pytest
from unittest.mock import MagicMock
from fastapi import Response, HTTPException
from backend.app.core.config import settings
from backend.app.core.security import (
    verify_credentials,
    create_access_token,
    decode_token,
    require_roles,
    normalize_role
)
from backend.app.models.schemas import (
    LoginRequest,
    BenchmarkingCompareRequest,
    ExportRequest
)
from backend.app.api.v1.auth import login, logout, get_me
from backend.app.api.v1.pro import compare_entities, export_csv, export_excel
from backend.app.services.export_service import export_service
from backend.app.services.camel_evaluator import camel_evaluator

def make_mock_request(client_ip="127.0.0.1", user_agent="PyTest-Pro"):
    req = MagicMock()
    req.client.host = client_ip
    req.headers.get.side_effect = lambda h: user_agent if h.lower() == "user-agent" else None
    return req

def test_pro_login_and_cookie_injection():
    """Valida autenticación institucional e inyección de la cookie HttpOnly."""
    req_body = LoginRequest(
        username="investigador.espoch",
        password="EspochPro2026#",
        role="investigador"
    )
    res = Response()
    mock_req = make_mock_request()

    user_resp = login(req=req_body, response=res, request=mock_req)
    assert user_resp.sub == "investigador.espoch"
    assert user_resp.role == "investigador"
    assert user_resp.authenticated is True
    assert "benchmarking" in user_resp.permissions

    # Validar cookie de sesión en cabeceras Set-Cookie
    set_cookie_header = res.headers.get("set-cookie", "")
    assert settings.COOKIE_NAME in set_cookie_header
    assert "HttpOnly" in set_cookie_header

def test_pro_login_invalid_password():
    """Valida que credenciales inválidas lancen HTTP 401."""
    req_body = LoginRequest(
        username="investigador.espoch",
        password="WrongPassword!",
        role="investigador"
    )
    res = Response()
    mock_req = make_mock_request()

    with pytest.raises(HTTPException) as exc:
        login(req=req_body, response=res, request=mock_req)
    assert exc.value.status_code == 401
    assert "Credenciales institucionales incorrectas" in exc.value.detail

def test_pro_get_me_profile():
    """Valida obtención de perfil con permisos RBAC."""
    user_payload = {
        "sub": "auditor.espoch",
        "role": "auditor",
        "name": "Auditor Financiero SFPS",
        "email": "auditor.espoch@espoch.edu.ec"
    }
    me = get_me(user=user_payload)
    assert me.sub == "auditor.espoch"
    assert me.role == "auditor"
    assert "export_excel" in me.permissions

def test_rbac_require_roles_dependency():
    """Valida el decorador de fábrica RBAC: rechaza roles no autorizados con 403."""
    checker = require_roles(["auditor", "administrador"])

    # Rol investigador intentando acceder a recurso exclusivo de auditor
    user_investigador = {"sub": "investigador.espoch", "role": "investigador"}
    with pytest.raises(HTTPException) as exc:
        checker(user=user_investigador)
    assert exc.value.status_code == 403
    assert "no cuenta con permisos suficientes" in exc.value.detail

    # Rol auditor admitido
    user_auditor = {"sub": "auditor.espoch", "role": "auditor"}
    assert checker(user=user_auditor) == user_auditor

def test_benchmarking_compare_analytics():
    """Valida motor analítico DuckDB para hasta 5 cooperativas con semáforo CAMEL."""
    req_body = BenchmarkingCompareRequest(
        entity_ids=["0190155722001", "0190115798001"],
        start_date="2024-01",
        end_date="2025-12",
        camel_dimension="calidad_de_activos"
    )
    mock_req = make_mock_request()
    user = {"sub": "investigador.espoch", "role": "investigador"}

    compare_res = compare_entities(req=req_body, request=mock_req, user=user)
    assert len(compare_res.entities) == 2
    assert len(compare_res.indicators) > 0
    assert compare_res.camel_dimension == "calidad_de_activos"

    # Verificar presencia de líneas base y evaluación de semáforo
    first_ind = compare_res.indicators[0]
    assert first_ind.segment1_baseline is not None
    assert first_ind.country_baseline is not None
    for ruc in req_body.entity_ids:
        eval_item = first_ind.entity_evaluations[ruc]
        assert eval_item.status in ["GREEN", "YELLOW", "RED"]
        assert eval_item.message != ""

def test_benchmarking_max_entities_limit():
    """Valida que más de 5 entidades sea rechazado por el esquema Pydantic."""
    with pytest.raises(ValueError) as exc:
        BenchmarkingCompareRequest(
            entity_ids=["1", "2", "3", "4", "5", "6"],
            start_date="2024-01",
            end_date="2025-12"
        )
    assert "5" in str(exc.value)

def test_export_csv_streaming_endpoint():
    """Valida endpoint de exportación en streaming CSV."""
    req_body = ExportRequest(
        entity_ids=["0190155722001"],
        start_date="2025-01",
        end_date="2025-12",
        camel_dimension="capital"
    )
    mock_req = make_mock_request()
    user = {"sub": "investigador.espoch", "role": "investigador"}

    stream_res = export_csv(req=req_body, request=mock_req, user=user)
    assert stream_res.media_type == "text/csv; charset=utf-8"
    assert "attachment; filename=" in stream_res.headers.get("content-disposition", "")

    # Consumir generador sincrónico subyacente
    chunks = list(export_service.stream_csv(req_body))
    full_text = "".join(chunks)
    assert "periodo,ruc,nombre_comercial,razon_social" in full_text
    assert "Jardin Azuayo" in full_text
    assert "solvencia_patrimonial" in full_text

def test_export_excel_endpoint():
    """Valida endpoint de exportación de libro Excel multi-pestaña."""
    req_body = ExportRequest(
        entity_ids=["0190155722001"],
        start_date="2025-01",
        end_date="2025-12",
        camel_dimension="liquidez"
    )
    mock_req = make_mock_request()
    user = {"sub": "auditor.espoch", "role": "auditor"}

    res = export_excel(req=req_body, request=mock_req, user=user)
    assert "spreadsheetml.sheet" in res.media_type
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    
    excel_bytes = export_service.generate_excel(req_body)
    assert len(excel_bytes) > 5000

def test_logout_clears_cookie():
    """Valida que logout elimine la cookie de sesión."""
    res = Response()
    mock_req = make_mock_request()
    user = {"sub": "investigador.espoch", "role": "investigador"}

    result = logout(response=res, request=mock_req, user=user)
    assert result["authenticated"] is False
    set_cookie_header = res.headers.get("set-cookie", "")
    assert settings.COOKIE_NAME in set_cookie_header
