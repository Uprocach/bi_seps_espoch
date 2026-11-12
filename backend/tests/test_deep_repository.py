"""
Pruebas de verificación de arquitectura profunda: AnalyticsRepository y ExportFormatter (Ticket 01)
Valida la consolidación de consultas DuckDB y la serialización binaria sin dependencias directas de base de datos.
"""
import pytest
from backend.app.services.repository import analytics_repository
from backend.app.services.export_formatter import export_formatter, format_coop_name
from backend.app.models.schemas import BenchmarkingCompareRequest, ExportRequest

def test_deep_repository_compare_entities():
    req = BenchmarkingCompareRequest(
        entity_ids=["0190155722001", "0190115798001"],
        start_date="2024-01",
        end_date="2025-12",
        camel_dimension=None
    )
    res = analytics_repository.compare_entities(req)
    assert len(res.entities) == 2
    assert len(res.indicators) > 0
    assert "0190155722001" in res.indicators[0].entity_values
    assert res.indicators[0].segment1_baseline is not None
    assert res.indicators[0].country_baseline is not None

def test_deep_repository_extract_microdata_rows():
    rows_gen = analytics_repository.extract_entity_microdata_rows(
        entity_ids=["0190155722001"],
        start_date="2025-01",
        end_date="2025-03"
    )
    rows = list(rows_gen)
    assert len(rows) > 0
    sample = rows[0]
    # Comprobar columnas del contrato de exportación
    assert len(sample) == 15
    assert sample[1] == "0190155722001" # RUC
    assert sample[12] in {"GREEN", "YELLOW", "RED"} # Estado semáforo

def test_export_formatter_stream_csv():
    dummy_rows = [
        ["2025-01", "0190155722001", "JARDIN AZUAYO", "COAC JARDIN AZUAYO", "SEGMENTO_1", "AZUAY", "morosidad", "Morosidad", "calidad_de_activos", "3.45", "4.12", "5.10", "GREEN", "SEPS v3.0", "Cumple"]
    ]
    chunks = list(export_formatter.stream_csv(iter(dummy_rows)))
    csv_text = "".join(chunks)
    assert csv_text.startswith("\ufeff") # BOM UTF-8
    assert "0190155722001" in csv_text
    assert "JARDIN AZUAYO" in csv_text

def test_export_formatter_generate_excel():
    req = BenchmarkingCompareRequest(
        entity_ids=["0190155722001"],
        start_date="2025-01",
        end_date="2025-03"
    )
    compare_res = analytics_repository.compare_entities(req)
    excel_bytes = export_formatter.generate_excel(
        compare_res=compare_res,
        indicators_spec=analytics_repository.spec.get("indicators", [])
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 1000
    # Comprobar firma binaria de archivo ZIP/XLSX (PK\x03\x04)
    assert excel_bytes.startswith(b"PK\x03\x04")
