# Ticket 02: Router de Supervisión Institucional y Contrato OpenAPI

Status: resolved
Blocked by: none (01 resuelto)

## Descripción
1. Crear `backend/app/api/v1/supervision.py` exponiendo los endpoints institucionales:
   - `POST /api/v1/supervision/benchmarking/compare`
   - `GET /api/v1/supervision/benchmarking/ranking`
   - `POST /api/v1/supervision/export/csv`
   - `POST /api/v1/supervision/export/excel`
2. Adaptar `backend/app/api/v1/pro.py` como pasarela delegada transparente hacia `/api/v1/supervision`.
3. Registrar el router `/supervision` en `backend/app/main.py`.
4. Formalizar las rutas de supervisión y sus esquemas en `contracts/openapi.yaml` y verificar linting con `npm run contract:lint` (Spectral).
5. Regenerar tipos TypeScript en `frontend/src/types/api.ts` vía `npm run frontend:codegen`.

## Criterios de Aceptación
1. `npm run contract:lint` aprueba sin errores ni advertencias de Spectral.
2. Endpoint `/api/v1/supervision/benchmarking/compare` protegido con RBAC (`investigador`, `auditor`, `administrador`).
3. Auditoría forense registrada en `audit_logs` de SQLite para cada acción de supervisión.

## Resolución
- Implementado router `/api/v1/supervision` en `backend/app/api/v1/supervision.py`.
- `backend/app/api/v1/pro.py` convertido en adaptador delegado para retrocompatibilidad total.
- Registrado `supervision_router` en `backend/app/main.py`.
- Añadidas rutas y esquemas de supervisión a `contracts/openapi.yaml`, pasando `npm run contract:lint` con 0 errores/warnings.
- Tipos de Frontend regenerados exitosamente en `frontend/src/types/api.ts`.
- Verificado con suite de pruebas `backend/tests/test_supervision_api.py` (72 tests pasando).
