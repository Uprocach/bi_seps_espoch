from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from fastapi.responses import StreamingResponse

from backend.app.core.security import require_roles
from backend.app.models.schemas import (
    BenchmarkingCompareRequest,
    BenchmarkingCompareResponse,
    BenchmarkingRankingResponse,
    ExportRequest
)
from backend.app.services.benchmarking_service import benchmarking_service
from backend.app.services.export_service import export_service
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/pro", tags=["Pro Analytics & Supervision"])

@router.post(
    "/benchmarking/compare",
    response_model=BenchmarkingCompareResponse,
    summary="Motor Analítico de Benchmarking Multi-Entidad",
    description="Contrasta hasta 5 cooperativas simultáneamente contra las líneas base del Segmento 1 y la media nacional en tiempo real con semáforo regulatorio CAMEL."
)
def compare_entities(
    req: BenchmarkingCompareRequest,
    request: Request,
    user: Annotated[dict, Depends(require_roles(["investigador", "auditor", "administrador"]))]
):
    # Ejecución analítica optimizada en DuckDB
    result = benchmarking_service.compare(req)

    # Registro de auditoría
    client_ip = request.client.host if request.client else None
    audit_service.log_event(
        user_sub=user.get("sub", "investigador"),
        user_role=user.get("role", "investigador"),
        action="benchmarking:compare",
        resource="/api/v1/pro/benchmarking/compare",
        details={
            "entities_count": len(req.entity_ids),
            "entity_ids": req.entity_ids,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "dimension": req.camel_dimension
        },
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent")
    )

    return result

@router.api_route(
    "/compare",
    methods=["GET", "POST"],
    summary="Motor Analítico de Benchmarking (Alias compatible)",
    description="Alias compatible hacia /benchmarking/compare para evaluación CAMEL multi-entidad.",
    include_in_schema=False
)
def compare_entities_alias(
    request: Request,
    user: Annotated[dict, Depends(require_roles(["investigador", "auditor", "administrador"]))],
    indicator: str | None = None,
    rucs: str | None = None,
    req_body: BenchmarkingCompareRequest | None = None
):
    if req_body is not None:
        return compare_entities(req=req_body, request=request, user=user)

    ruc_list = [r.strip() for r in (rucs or "").split(",") if r.strip()]
    if not ruc_list:
        ruc_list = ["0190155722001"]

    req = BenchmarkingCompareRequest(
        entity_ids=ruc_list[:5],
        start_date="2024-01",
        end_date="2025-12",
        camel_dimension=None
    )
    return compare_entities(req=req, request=request, user=user)

@router.get(
    "/benchmarking/ranking",
    response_model=BenchmarkingRankingResponse,
    summary="Ranking Nacional de COACs por Ficha Metodológica",
    description="Genera el ranking de cooperativas ordenado según la polaridad y desempeño del ratio analizado con semáforo regulatorio CAMEL."
)
def get_benchmarking_ranking(
    indicator_id: Annotated[str, Query(description="Identificador del indicador")],
    period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="Periodo de corte YYYY-MM")] = None,
    segment: Annotated[str | None, Query(description="Filtrar por segmento (ej. SEGMENTO_1, SEGMENTO_2, SEGMENTO_3)")] = None,
    province: Annotated[str | None, Query(description="Filtrar por nombre o código de provincia")] = None,
    rucs: Annotated[list[str] | None, Query(description="Lista de hasta 10 RUCs para contrastar ranking relativo")] = None,
    limit: Annotated[int, Query(ge=1, le=250, description="Límite de cooperativas a rankear")] = 250,
    user: Annotated[dict, Depends(require_roles(["investigador", "auditor", "administrador"]))] = None
):
    return benchmarking_service.get_entity_ranking(
        indicator_id=indicator_id,
        period=period,
        segment=segment,
        province=province,
        rucs=rucs,
        limit=limit
    )

@router.post(
    "/export/csv",
    summary="Exportación y Streaming de Microdatos en CSV",
    description="Canaliza mediante StreamingResponse los microdatos de las cooperativas seleccionadas con evaluación de semáforo normativo sin saturar la memoria del servidor."
)
def export_csv(
    req: ExportRequest,
    request: Request,
    user: Annotated[dict, Depends(require_roles(["investigador", "auditor", "administrador"]))]
):
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"espoch_sfps_microdatos_{timestamp_str}.csv"

    # Auditoría del evento de descarga masiva
    client_ip = request.client.host if request.client else None
    audit_service.log_event(
        user_sub=user.get("sub", "investigador"),
        user_role=user.get("role", "investigador"),
        action="export:csv",
        resource="/api/v1/pro/export/csv",
        details={
            "entity_ids": req.entity_ids,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "dimension": req.camel_dimension,
            "filename": filename
        },
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent")
    )

    return StreamingResponse(
        export_service.stream_csv(req),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.post(
    "/export/excel",
    summary="Exportación de Reporte Multi-Pestaña en Excel",
    description="Genera y emite un libro Excel multi-pestaña (Resumen Benchmarking con semáforos, Series Históricas y Ficha Metodológica SEPS) formateado profesionalmente para auditoría y comités de riesgo."
)
def export_excel(
    req: ExportRequest,
    request: Request,
    user: Annotated[dict, Depends(require_roles(["auditor", "administrador"]))]
):
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"espoch_sfps_benchmarking_camel_{timestamp_str}.xlsx"

    excel_bytes = export_service.generate_excel(req)

    # Auditoría del evento de descarga masiva Excel
    client_ip = request.client.host if request.client else None
    user_role = user.get("role") or user.get("normalized_role") or "auditor"
    audit_service.log_event(
        user_sub=user.get("sub", "auditor"),
        user_role=user_role,
        action="export:excel",
        resource="/api/v1/pro/export/excel",
        details={
            "entity_ids": req.entity_ids,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "dimension": req.camel_dimension,
            "filename": filename,
            "bytes_size": len(excel_bytes)
        },
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent")
    )

    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(excel_bytes)),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
