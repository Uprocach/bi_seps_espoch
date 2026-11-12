"""
Adaptador de compatibilidad para BenchmarkingService.
Delega todas las operaciones analíticas al repositorio analítico consolidado (AnalyticsRepository),
eliminando la duplicación de conexiones DuckDB y centralizando la ejecución de consultas.
"""
from pathlib import Path
from backend.app.services.repository import AnalyticsRepository, analytics_repository
from backend.app.models.schemas import (
    BenchmarkingCompareRequest,
    BenchmarkingCompareResponse,
    BenchmarkingRankingResponse
)

class BenchmarkingService:
    def __init__(self, mart_dir: Path | None = None):
        self._repo = AnalyticsRepository(mart_dir) if mart_dir else analytics_repository

    @property
    def spec(self):
        return self._repo.spec

    @property
    def mart_dir(self):
        return self._repo.mart_dir

    def get_cursor(self):
        return self._repo.get_cursor()

    def compare(self, req: BenchmarkingCompareRequest) -> BenchmarkingCompareResponse:
        return self._repo.compare_entities(req)

    def get_entity_ranking(
        self,
        indicator_id: str,
        period: str | None = None,
        segment: str | None = None,
        province: str | None = None,
        rucs: list[str] | None = None,
        limit: int = 250
    ) -> BenchmarkingRankingResponse:
        return self._repo.get_entity_ranking(
            indicator_id=indicator_id,
            period=period,
            segment=segment,
            province=province,
            rucs=rucs,
            limit=limit
        )

benchmarking_service = BenchmarkingService()
