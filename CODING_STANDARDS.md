# Coding Standards

Criterios de juicio para revisión de código (`/code-review`). Las reglas mecánicas viven en `scripts/check-guardrails.mjs`, `contracts/.spectral.yaml`, `tsc` y `ruff` (CI); aquí solo se documentan decisiones que requieren criterio humano.

## 1. Vocabulario de dominio (SEPS / SFPS)
- Usa los términos canónicos de `GLOSSARY.md` y `docs/adr/` en textos visibles, rutas, comentarios y documentación (ej. **Benchmarking Institucional**, nunca *Benchmarking Pro*).
- No dupliques definiciones de tipos OpenAPI en el frontend: usa `src/types/api.ts` (vía `src/services/httpClient.ts`) como fuente de verdad de contratos HTTP.

## 2. Arquitectura y profundidad de módulos
- **Backend:** la lógica analítica y de exportación reside en `AnalyticsRepository` (`backend/app/services/repository.py`); los routers (`backend/app/api/v1/`) solo validan entrada, aplican RBAC/ETag y traducen errores de dominio a HTTP.
- **Persistencia Dual:** todo acceso SQLite/Postgres pasa por `DualDatabaseAdapter` (`backend/app/services/dual_db.py`) para mantener un único punto de dialecto.
- **Frontend:** separa lógica pura de dominio y formateo (`src/lib/`), estado/consultas (`src/hooks/` + `httpClient.ts`) y componentes de presentación (`src/components/`). Evita `setState` dentro de `useMemo` o efectos derivados innecesarios.
- **Helpers compartidos:** extrae utilidades reutilizables (ej. `formatIndicatorValue` en `src/lib/utils.ts`) cuando el mismo formateo o regla aparezca en más de una vista.

## 3. Contratos de fallo explícitos
- **Auditoría (`AuditService`):** política *fail-open* — si falla la escritura en BD, registra `logger.error` sin interrumpir la petición del usuario.
- **Ciclo de Marts (`MartPathProvider.atomic_switch`):** política *fail-closed* — toda promoción de staging valida integridad mediante el Gatekeeper (`MartValidationError` → HTTP `422`).
