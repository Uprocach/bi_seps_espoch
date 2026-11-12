"""
Adaptador de compatibilidad para ExportService.
Delega la extracción de datos a AnalyticsRepository y el formateo binario a ExportFormatter,
eliminando completamente las conexiones redundantes DuckDB y unificando el pipeline de exportación.
"""
from typing import Generator
from pathlib import Path
from backend.app.services.repository import AnalyticsRepository, analytics_repository
from backend.app.services.export_formatter import ExportFormatter, export_formatter, format_coop_name
from backend.app.models.schemas import ExportRequest, BenchmarkingCompareRequest
from backend.app.services.camel_evaluator import camel_evaluator

class ExportService:
    def __init__(self, mart_dir: Path | None = None):
        self._repo = AnalyticsRepository(mart_dir) if mart_dir else analytics_repository
        self._formatter = export_formatter

    def stream_csv(self, req: ExportRequest, delimiter: str = ",") -> Generator[str, None, None]:
        rows_gen = self._repo.extract_entity_microdata_rows(
            entity_ids=req.entity_ids,
            start_date=req.start_date,
            end_date=req.end_date,
            camel_dimension=req.camel_dimension
        )
        return self._formatter.stream_csv(rows_gen, delimiter=delimiter)

    def generate_excel(self, req: ExportRequest) -> bytes:
        compare_req = BenchmarkingCompareRequest(
            entity_ids=req.entity_ids,
            start_date=req.start_date,
            end_date=req.end_date,
            camel_dimension=req.camel_dimension
        )
        compare_res = self._repo.compare_entities(compare_req)
        return self._formatter.generate_excel(
            compare_res=compare_res,
            indicators_spec=self._repo.spec.get("indicators", []),
            camel_config=camel_evaluator._config
        )

export_service = ExportService()
