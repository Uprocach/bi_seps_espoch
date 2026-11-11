from fastapi import APIRouter, Response, Request
from backend.app.models.schemas import FiltersMetadata
from backend.app.services.repository import AnalyticsRepository

router = APIRouter(prefix="/metadata", tags=["Metadata"])
repo = AnalyticsRepository()

@router.get(
    "/filters",
    response_model=FiltersMetadata,
    operation_id="getMetadataFilters",
    summary="Catálogos de filtros",
    description="Devuelve los valores disponibles para los filtros globales del dashboard."
)
def get_metadata_filters(response: Response = Response(), request: Request = None):
    response.headers["Cache-Control"] = "public, max-age=3600"
    data = repo.get_metadata_filters()
    return data
