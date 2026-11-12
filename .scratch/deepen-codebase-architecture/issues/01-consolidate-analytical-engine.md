# Ticket 01: Consolidación del Motor Analítico DuckDB y Formateador de Exportación

Status: resolved
Blocked by: none

## Descripción
Consolidar el acceso a DuckDB y las consultas a cubos Parquet en `AnalyticsRepository` (`backend/app/services/repository.py`):
1. Integrar el método `compare_entities` (absorbiendo la lógica de `BenchmarkingService` y eliminando `get_benchmark_matrix` redundante) utilizando un único pool de conexiones DuckDB thread-safe.
2. Integrar el método `extract_entity_microdata_rows` para la consulta tabular de microdatos requerida en exportaciones.
3. Crear `ExportFormatter` en `backend/app/services/export_formatter.py` con métodos `stream_csv` y `generate_excel`, completamente desacoplados de DuckDB y Parquet.
4. Desprender la dependencia de `BenchmarkingService` y `ExportService` hacia el nuevo motor analítico unificado.

## Criterios de Aceptación
1. `AnalyticsRepository` centraliza todas las consultas a `dim_*` y `fct_*` con un único pool DuckDB.
2. `ExportFormatter` genera CSV con UTF-8 BOM y Excel con formato CAMEL recibiendo diccionarios estructurados.
3. Pruebas unitarias de repositorio y formateador ejecutándose sin errores.

## Resolución
- Implementado `AnalyticsRepository.compare_entities`, `get_entity_ranking` y `extract_entity_microdata_rows` en `backend/app/services/repository.py`.
- Creado `ExportFormatter` en `backend/app/services/export_formatter.py`.
- Convertidos `BenchmarkingService` y `ExportService` en adaptadores delgados delegando en `AnalyticsRepository` y `ExportFormatter`.
- Verificado con 68 tests de Pytest aprobados (`backend/tests/test_deep_repository.py`).
