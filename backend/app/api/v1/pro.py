"""
Adaptador de compatibilidad para el router histórico /api/v1/pro (ADR-0004).
Redirige y delega transparentemente todas las operaciones hacia /api/v1/supervision,
garantizando cero regresiones mientras los clientes se migran a la nomenclatura institucional.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from backend.app.core.security import require_roles
from backend.app.api.v1.supervision import (
    compare_entities,
    get_benchmarking_ranking,
    export_csv,
    export_excel
)
from backend.app.models.schemas import BenchmarkingCompareRequest

router = APIRouter(prefix="/pro", tags=["Pro Analytics & Supervision (Legacy Alias)"], include_in_schema=False)

# Endpoints delegados
router.add_api_route("/benchmarking/compare", compare_entities, methods=["POST"])
router.add_api_route("/benchmarking/ranking", get_benchmarking_ranking, methods=["GET"])
router.add_api_route("/export/csv", export_csv, methods=["POST"])
router.add_api_route("/export/excel", export_excel, methods=["POST"])

# Alias histórico /compare
@router.api_route("/compare", methods=["GET", "POST"], include_in_schema=False)
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
