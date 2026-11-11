"""
Unit & Integration Test Suite for FastAPI Backend
Validates API responses, RBAC security, SQL injection defense and error contracts against contracts/openapi.yaml.
"""

import pytest
from fastapi import Response
from backend.app.api.v1.metadata import get_metadata_filters
from backend.app.api.v1.entities import list_entities
from backend.app.api.v1.indicators import get_indicator_series, get_benchmark_matrix
from backend.app.core.errors import APIProblemException
from backend.app.core.security import create_access_token, decode_token
from backend.app.services.repository import AnalyticsRepository
from backend.app.models.schemas import (
    FiltersMetadata,
    EntityListResponse,
    IndicatorSeriesResponse
)

PRO_USER = {"sub": "investigador.espoch", "role": "researcher"}

def test_metadata_filters_contract():
    """Valida que /api/v1/metadata/filters cumpla con el esquema FiltersMetadata y notas metodológicas."""
    res = Response()
    data = get_metadata_filters(res)
    assert res.headers.get("Cache-Control") == "public, max-age=3600"
    
    # Validar con Pydantic Schema estricto de OpenAPI
    validated = FiltersMetadata.model_validate(data)
    assert len(validated.segments) >= 4
    assert any(s.code == "SEGMENTO_1" for s in validated.segments)
    assert len(validated.provinces) == 24
    assert any(p.code == "01" and p.name == "AZUAY" for p in validated.provinces)
    assert validated.periods.latest in ["2025-12", "2026-09"]
    assert len(validated.periods.available) >= 96
    
    ind_ids = [i.id for i in validated.indicators]
    assert "morosidad_cartera_total" in ind_ids
    assert "cobertura_cartera_improductiva" in ind_ids
    assert "roa" in ind_ids
    assert "solvencia_patrimonial" in ind_ids
    assert "seps_62_solvencia" in ind_ids

    # Nota metodológica presente en ROA / ROE
    roa_meta = next(i for i in validated.indicators if i.id == "roa")
    assert roa_meta.methodological_note is not None
    assert "Excedente" in roa_meta.methodological_note

def test_entities_list_contract_and_filters():
    """Valida que /api/v1/entities pagine y filtre correctamente según el contrato."""
    # 1. Paginación
    data = list_entities(page=1, page_size=5)
    validated = EntityListResponse.model_validate(data)
    assert len(validated.data) == 5
    assert validated.pagination.total_items >= 200
    assert validated.pagination.page == 1
    assert validated.pagination.page_size == 5

    # 2. Búsqueda por texto (Jardín Azuayo)
    search_data = list_entities(q="jardin")
    search_val = EntityListResponse.model_validate(search_data)
    assert len(search_val.data) >= 1
    top_entity = search_val.data[0]
    assert "JARDIN AZUAYO" in top_entity.razon_social
    assert top_entity.province.name == "AZUAY"
    assert top_entity.total_assets_usd > 1_000_000_000

    # 3. Filtro por segmento
    seg_data = list_entities(segment=["SEGMENTO_1"])
    seg_val = EntityListResponse.model_validate(seg_data)
    assert all(e.segment == "SEGMENTO_1" for e in seg_val.data)

def test_entities_sql_injection_defense():
    """Valida que campos de ordenamiento fuera de whitelist sean rechazados con 400."""
    with pytest.raises(APIProblemException) as exc:
        list_entities(sort="total_assets_usd; DROP TABLE dim_entities;--")
    assert exc.value.status_code == 400
    assert "no está permitido" in exc.value.detail

    with pytest.raises(APIProblemException) as exc2:
        list_entities(sort="non_existent_column")
    assert exc2.value.status_code == 400

def test_indicators_series_country():
    """Valida la serie país para morosidad total conforme a IndicatorSeriesResponse (acceso público)."""
    data = get_indicator_series(
        indicator="morosidad_cartera_total",
        level="country",
        from_="2025-01",
        to="2025-12"
    )
    validated = IndicatorSeriesResponse.model_validate(data)
    assert validated.indicator.id == "morosidad_cartera_total"
    assert validated.level == "country"
    assert len(validated.series) == 1
    
    series_points = validated.series[0].points
    assert len(series_points) == 12
    # Cierre diciembre 2025: 7.84%
    dic_point = next(p for p in series_points if p.period == "2025-12")
    assert round(dic_point.value, 2) == 7.84
    assert dic_point.entity_count >= 200

def test_indicators_series_segment():
    """Valida la serie segmento para cobertura de cartera conforme a IndicatorSeriesResponse (acceso público)."""
    data = get_indicator_series(
        indicator="cobertura_cartera_improductiva",
        level="segment",
        segment=["SEGMENTO_1", "SEGMENTO_2"],
        from_="2025-10",
        to="2025-12"
    )
    validated = IndicatorSeriesResponse.model_validate(data)
    assert len(validated.series) == 2
    seg1 = next(s for s in validated.series if s.key == "SEGMENTO_1")
    assert len(seg1.points) == 3
    assert seg1.points[-1].value > 90.0

def test_indicators_series_entity_public_and_accredited_access():
    """Valida que la consulta de series a nivel entidad sea accesible tanto para público como para acreditados."""
    ruc = "0190155722001"

    # 1. Acceso público sin autenticación (user=None) devuelve 200 con la serie de la cooperativa
    data_public = get_indicator_series(
        indicator="roa",
        level="entity",
        ruc=[ruc],
        from_="2025-01",
        to="2025-12",
        user=None
    )
    validated_public = IndicatorSeriesResponse.model_validate(data_public)
    assert len(validated_public.series) == 1
    assert validated_public.series[0].points[0].value is not None

    # 2. Acceso con token / usuario acreditado
    data = get_indicator_series(
        indicator="roa",
        level="entity",
        ruc=[ruc],
        from_="2025-01",
        to="2025-12",
        user=PRO_USER
    )
    validated = IndicatorSeriesResponse.model_validate(data)
    assert len(validated.series) == 1
    assert len(validated.series) == 1
    assert validated.series[0].key == ruc
    assert "JARDIN AZUAYO" in validated.series[0].label
    assert len(validated.series[0].points) == 12
    assert validated.indicator.methodological_note is not None

def test_consolidated_benchmark_matrix():
    """Valida el endpoint consolidado de matriz de benchmarking para mitigar cascada de red N+1."""
    matrix_res = get_benchmark_matrix(
        ruc=["0190155722001", "0190097510001"],
        period="2025-12",
        user=PRO_USER
    )
    assert "matrix" in matrix_res
    assert len(matrix_res["matrix"]) >= 8
    # Verificar que contiene tanto valores de las entidades como del segmento 1 y país
    morosidad_row = next(r for r in matrix_res["matrix"] if r["indicator_id"] == "morosidad_cartera_total")
    assert "0190155722001" in morosidad_row["entity_values"]
    assert morosidad_row["segment1_avg"] is not None
    assert morosidad_row["country_avg"] is not None

def test_problem_details_exceptions():
    """Valida que los errores de negocio lancen APIProblemException con códigos RFC 9457."""
    # 1. level=entity sin RUC con usuario Pro -> 422
    with pytest.raises(APIProblemException) as exc1:
        get_indicator_series(indicator="roa", level="entity", user=PRO_USER)
    assert exc1.value.status_code == 422
    assert "ruc" in str(exc1.value.errors)

    # 2. Indicador inexistente -> 400
    with pytest.raises(APIProblemException) as exc2:
        get_indicator_series(indicator="indicador_inexistente", level="country")
    assert exc2.value.status_code == 400

    # 3. from > to -> 422
    with pytest.raises(APIProblemException) as exc3:
        get_indicator_series(indicator="roa", level="country", from_="2025-12", to="2025-01")
    assert exc3.value.status_code == 422

def test_solvencia_legal_acpr_ficha_62():
    """Valida el indicador regulatorio de Solvencia Legal ACPR (Ficha 62)."""
    # Nivel País
    data_country = get_indicator_series(
        indicator="seps_62_solvencia",
        level="country",
        from_="2025-01",
        to="2025-12"
    )
    val_country = IndicatorSeriesResponse.model_validate(data_country)
    assert val_country.indicator.id == "seps_62_solvencia"
    assert val_country.indicator.seps_ficha_number == 62
    assert len(val_country.series[0].points) == 12
    # El promedio de solvencia legal del sistema cooperativo supera el 14%
    assert val_country.series[0].points[-1].value > 12.0

    # Nivel Entidad (Jardín Azuayo con usuario Pro)
    data_ent = get_indicator_series(
        indicator="seps_62_solvencia",
        level="entity",
        ruc=["0190155722001"],
        from_="2025-12",
        to="2025-12",
        user=PRO_USER
    )
    val_ent = IndicatorSeriesResponse.model_validate(data_ent)
    assert val_ent.series[0].points[0].value > 9.0  # Cumple con el mínimo legal 9%

def test_http_cache_and_etag():
    """Valida la inyección de cabeceras ETag, Cache-Control y respuesta 304 Not Modified."""
    res = Response()
    data = get_indicator_series(
        indicator="morosidad_cartera_total",
        level="country",
        from_="2025-01",
        to="2025-12",
        response=res
    )
    assert res.headers.get("Cache-Control") == "public, max-age=86400"
    etag = res.headers.get("ETag")
    assert etag is not None and etag.startswith('W/"')

    # Simular petición subsecuente con If-None-Match idéntico
    class MockRequest:
        headers = {"if-none-match": etag}

    res_304 = get_indicator_series(
        indicator="morosidad_cartera_total",
        level="country",
        from_="2025-01",
        to="2025-12",
        request=MockRequest()
    )
    assert isinstance(res_304, Response)
    assert res_304.status_code == 304

def test_auth_token_credentials_protection():
    """Valida la mitigación NUEVA-01: Auto-emisión bloqueada, requiere credenciales institucionales válidas."""
    from backend.app.api.v1.auth import get_auth_token, LoginRequest
    from fastapi import HTTPException

    # 1. Contraseña incorrecta debe ser rechazada con 401
    with pytest.raises(HTTPException) as exc_wrong_pw:
        get_auth_token(LoginRequest(username="investigador.espoch", password="WrongPassword#"))
    assert exc_wrong_pw.value.status_code == 401
    assert "Credenciales institucionales incorrectas" in exc_wrong_pw.value.detail

    # 2. Usuario inexistente debe ser rechazado con 401
    with pytest.raises(HTTPException) as exc_wrong_user:
        get_auth_token(LoginRequest(username="hacker.anonimo", password="EspochPro2026#"))
    assert exc_wrong_user.value.status_code == 401

    # 3. Rol no autorizado para el usuario debe ser rechazado con 401
    with pytest.raises(HTTPException) as exc_wrong_role:
        get_auth_token(LoginRequest(username="investigador.espoch", password="EspochPro2026#", role="superadmin_ficticio"))
    assert exc_wrong_role.value.status_code == 401

    # 4. Credenciales válidas emiten un JWT firmado y decodificable
    auth_res = get_auth_token(LoginRequest(username="investigador.espoch", password="EspochPro2026#", role="researcher"))
    assert auth_res["token_type"] == "bearer"
    assert auth_res["role"] == "researcher"
    assert auth_res["user"] == "investigador.espoch"
    payload = decode_token(auth_res["access_token"])
    assert payload["sub"] == "investigador.espoch"
    assert payload["role"] == "researcher"

def test_hive_partitioned_queries():
    """Valida la mitigación NUEVA-02: El repositorio DuckDB consulta a través del árbol particionado Hive."""
    repo = AnalyticsRepository()
    partitioned_pattern = repo._p_entity_partitioned()
    assert "partitioned" in partitioned_pattern
    assert partitioned_pattern.endswith(".parquet")

    # Ejecutar consulta a través del repositorio y validar que retorne datos consistentes
    series_res = repo.get_indicator_series(
        indicator="morosidad_cartera_total",
        level="entity",
        ruc=["0190155722001"],
        from_period="2025-01",
        to_period="2025-12"
    )
    assert len(series_res["series"]) == 1
    assert len(series_res["series"][0]["points"]) == 12
    assert series_res["series"][0]["points"][0]["value"] > 0


