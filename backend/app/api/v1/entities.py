from typing import Annotated
from fastapi import APIRouter, Query
from backend.app.models.schemas import EntityListResponse
from backend.app.services.repository import AnalyticsRepository

router = APIRouter(prefix="/entities", tags=["Entities"])
repo = AnalyticsRepository()

@router.get(
    "",
    response_model=EntityListResponse,
    operation_id="listEntities",
    summary="Listado de entidades",
    description="Lista paginada de cooperativas y mutualistas con filtros por segmento, provincia, texto libre y estado de reporte."
)
def list_entities(
    segment: Annotated[list[str] | None, Query(description="Uno o varios segmentos")] = None,
    province: Annotated[list[str] | None, Query(description="Uno o varios códigos de provincia DPA de 2 dígitos")] = None,
    q: Annotated[str | None, Query(min_length=2, max_length=100, description="Búsqueda por razón social o RUC")] = None,
    active: Annotated[bool | None, Query(description="Filtrar por estado activo")] = None,
    sort: Annotated[str, Query(description="Campo de ordenamiento")] = "-total_assets_usd",
    page: Annotated[int, Query(ge=1, description="Número de página")] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000, description="Tamaño de página")] = 50
):
    return repo.list_entities(
        segment=segment,
        province=province,
        q=q,
        active=active,
        sort=sort,
        page=page,
        page_size=page_size
    )
