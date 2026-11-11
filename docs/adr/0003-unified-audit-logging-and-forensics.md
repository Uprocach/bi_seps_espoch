# 0003. Unificación de Auditoría Forense en SQLite Persistente y Blindaje de Consultas

- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Decisores:** Investigador Principal / Arquitectura de Software ESPOCH-DI-060
- **Hallazgos Subsanados:** AUD-13, AUD-14, AUD-15, AUD-16, AUD-17

## Contexto

Durante la auditoría técnica integral del sistema bajo metodología SDD, se identificaron cuatro riesgos y brechas de diseño:
1. **Volatilidad de la bitácora en Docker (AUD-13):** `AuditService` persistía eventos en `data/interim/audit_events.jsonl`, pero dicho directorio no estaba montado en `docker-compose.yml`, arriesgando la pérdida total de registros ante reinicios de contenedor en Portainer.
2. **Brecha de Dominio (AUD-14):** Los roles *auditor* y *administrador* disponían del permiso formal `view_audit_logs`, pero carecían de endpoint en OpenAPI y de interfaz en el Frontend.
3. **Concurrencia en SQLite (AUD-15):** Uvicorn opera con 4 workers en producción y la base de datos `data/users.db` carecía de `PRAGMA journal_mode = WAL;` y timeout de contención.
4. **Inconsistencia de Parámetros (AUD-16 y AUD-17):** `BenchmarkingService` y `ExportService` utilizaban interpolación de cadenas de texto para filtrar RUCs en DuckDB y duplicaban rutas y conexiones Parquet.

## Decisión

1. **Persistencia Unificada en `data/users.db`:**
   - Se crea la tabla indexada `audit_logs` en SQLite con índices en `timestamp`, `user_sub` y `action`.
   - Se activa obligatoriamente `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;` y `PRAGMA busy_timeout = 5000;`, garantizando concurrencia óptima multi-worker sin bloqueos de archivo.
2. **Endpoint y Contrato OpenAPI para Auditoría:**
   - Se formaliza en `contracts/openapi.yaml` la ruta `GET /api/v1/admin/audit-logs` con paginación (`limit`, `offset`) y filtros por usuario, acción y rango de fechas.
   - Acceso restringido vía RBAC para roles `auditor` y `administrador`.
3. **Módulo Interactivo en Frontend (`AuditLogsView`):**
   - Se implementa la interfaz visual para inspeccionar eventos en tiempo real, filtrar acciones, revisar IPs y desplegar el payload JSON detallado.
4. **Centralización y Blindaje Parametrizado:**
   - Se crea el módulo `MartPathProvider` (`backend/app/services/mart_provider.py`) que unifica la resolución de particiones Hive en Parquet y conexiones DuckDB.
   - Se parametriza con placeholders `?` el filtrado de RUCs en DuckDB y se valida el formato con regex estricto `^\d{10,13}$` en Pydantic.

## Consecuencias

- **Persistencia Garantizada:** Cero pérdida de logs forenses al recrear o actualizar contenedores Docker en Portainer.
- **Transparencia y Compliance:** Auditores y directivos disponen de un visor completo de trazabilidad de descargas masivas y cambios de estado.
- **Resiliencia Operativa:** Eliminación del riesgo de bloqueo `database is locked` bajo carga concurrente de peticiones.
