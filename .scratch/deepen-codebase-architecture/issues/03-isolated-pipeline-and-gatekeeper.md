# Ticket 03: Aislamiento del Pipeline de Datos y Gatekeeper Funcional Puro

Status: resolved
Blocked by: none (01 resuelto)

## Descripción
1. Refactorizar `etl/monthly_pipeline.py` para desacoplar el pipeline de variables de entorno:
   - Pasar el directorio objetivo (`target_dir: Path`) explícitamente a las funciones de construcción y validación.
   - Implementar `verify_mart_integrity(target_dir: Path) -> ValidationReport` que ejecute verificaciones analíticas directas con DuckDB (existencia de Parquet, no-vacíos, integridad referencial de dimensiones y claves de periodo).
2. Refactorizar `backend/app/services/sync_manager.py`:
   - Eliminar `os.environ["MART_DIR"] = str(staging_dir)`.
   - Invocar directamente `verify_mart_integrity(staging_dir)` en lugar de `unittest.TestLoader().discover()`.
   - Registrar el `ValidationReport` en la bitácora `audit_logs` de SQLite al ejecutar el cambio atómico.

## Criterios de Aceptación
1. Cero mutaciones de `os.environ` durante la ejecución de la sincronización web.
2. `verify_mart_integrity()` valida exitosamente `data/processed/mart` y `mart_staging` sin disparar el test runner de unittest.
3. El proceso de background sync opera de forma 100% thread-safe.

## Resolución
- En `etl/build_marts.py`: parametrizado `build_marts(target_dir: Path | None = None)` con `out_dir` explícito sin mutar `os.environ`.
- En `etl/monthly_pipeline.py`: implementada función pura `verify_mart_integrity(target_dir: Path) -> Dict[str, Any]` que ejecuta 7 controles analíticos rigurosos sin dependencias de test runners en proceso.
- En `backend/app/services/sync_manager.py`: reemplazadas las mutaciones globales de `os.environ` por llamadas explícitas a `build_marts(target_dir=staging_dir)` y `verify_mart_integrity(staging_dir)`, registrando `validation_report` en SQLite.
- Verificado con `npm run etl:test` y `npm run backend:test` (72 tests aprobados).
