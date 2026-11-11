import hashlib
from typing import Annotated
from fastapi import APIRouter, Query, Depends, Response, Request
from backend.app.models.schemas import IndicatorSeriesResponse, AggregationLevel
from backend.app.services.repository import AnalyticsRepository
from backend.app.core.security import get_current_user_optional, normalize_role
from backend.app.core.errors import APIProblemException

router = APIRouter(prefix="/indicators", tags=["Indicators"])
repo = AnalyticsRepository()

ALLOWED_ROLES = {"investigador", "auditor", "administrador", "researcher", "admin"}

@router.get(
    "/metadata",
    summary="Catálogos de filtros y metadatos (Alias)",
    description="Alias compatible hacia /api/v1/metadata/filters para consulta pública de metadatos.",
    include_in_schema=False
)
def get_indicators_metadata(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600"
    return repo.get_metadata_filters()

@router.get(
    "/benchmark-matrix",
    summary="Matriz consolidada de benchmarking CAMEL",
    description="Devuelve la matriz de benchmarking comparativa con valores de entidad, medias de Segmento 1 y País en una única consulta con soporte ETag/304."
)
def get_benchmark_matrix(
    ruc: Annotated[list[str] | None, Query(description="RUCs de las cooperativas a comparar")] = None,
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo de corte YYYY-MM")] = None,
    user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    response: Response = Response(),
    request: Request = None
):
    if not user or (normalize_role(user.get("role")) not in ALLOWED_ROLES and user.get("role") not in ALLOWED_ROLES):
        raise APIProblemException(
            status_code=403,
            title="Acceso Denegado",
            detail="La matriz de benchmarking analítica multi-entidad requiere credenciales institucionales acreditadas."
        )

    if not ruc:
        raise APIProblemException(
            status_code=422,
            title="Error de validación",
            detail="Debe especificar al menos un parámetro 'ruc' para consultar la matriz de benchmarking.",
            errors=[{"field": "ruc", "message": "Field required"}]
        )

    result = repo.get_benchmark_matrix(rucs=ruc, period=period)

    # Capa de Caché HTTP ETag y Cache-Control: max-age=86400
    effective_period = result.get("period", period or "")
    etag_seed = f"benchmark:{sorted(ruc)}:{effective_period}:{len(result.get('matrix', []))}"
    etag_val = f'W/"{hashlib.sha256(etag_seed.encode()).hexdigest()[:16]}"'

    if request and request.headers.get("if-none-match") == etag_val:
        return Response(status_code=304, headers={"ETag": etag_val, "Cache-Control": "public, max-age=86400"})

    if response:
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["ETag"] = etag_val

    return result

@router.get(
    "/series",
    response_model=IndicatorSeriesResponse,
    operation_id="getIndicatorSeries",
    summary="Series de tiempo de un indicador",
    description="Devuelve la serie mensual de un indicador para el nivel solicitado con cabeceras ETag y Cache-Control."
)
def get_indicator_series(
    indicator: Annotated[str, Query(description="Identificador del indicador")],
    level: Annotated[AggregationLevel, Query(description="Nivel de agregación")],
    segment: Annotated[list[str] | None, Query(description="Filtrar por segmentos")] = None,
    province: Annotated[list[str] | None, Query(description="Filtrar por provincias")] = None,
    ruc: Annotated[list[str] | None, Query(description="RUCs de las entidades")] = None,
    from_: Annotated[str | None, Query(alias="from", pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo inicial YYYY-MM")] = None,
    to: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo final YYYY-MM")] = None,
    user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    response: Response = Response(),
    request: Request = None
):
    result = repo.get_indicator_series(
        indicator=indicator,
        level=level,
        segment=segment,
        province=province,
        ruc=ruc,
        from_period=from_,
        to_period=to
    )

    # Capa de Caché HTTP ETag y Cache-Control: max-age=86400 (Frente 3)
    p_from = result.get("period_range", {}).get("from", from_ or "")
    p_to = result.get("period_range", {}).get("to", to or "")
    etag_seed = f"series:{indicator}:{level}:{p_from}:{p_to}:{sorted(segment or [])}:{sorted(province or [])}:{sorted(ruc or [])}"
    etag_val = f'W/"{hashlib.sha256(etag_seed.encode()).hexdigest()[:16]}"'

    if request and request.headers.get("if-none-match") == etag_val:
        return Response(status_code=304, headers={"ETag": etag_val, "Cache-Control": "public, max-age=86400"})

    if response:
        response.headers["Cache-Control"] = "public, max-age=86400"
        response.headers["ETag"] = etag_val

    return result
