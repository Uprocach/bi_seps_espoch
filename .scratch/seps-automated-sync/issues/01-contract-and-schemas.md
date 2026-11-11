# Ticket 01: Contrato OpenAPI 3.1.0 y Esquemas de Sincronización Web

Status: ready-for-agent
Blocked by: none

## Descripción
Formalizar en `contracts/openapi.yaml` los endpoints administrativos para la sincronización web con el portal de la SEPS:
- `POST /api/v1/admin/pipeline-sync`
- `GET /api/v1/admin/pipeline-sync-status`

Crear los esquemas correspondientes:
- `PipelineSyncRequest`
- `PipelineSyncStatusResponse`

## Criterios de Aceptación
1. `npm run contract:lint` (Spectral) pasa con 0 errores y 0 advertencias.
2. Los modelos Pydantic están definidos en `backend/app/models/schemas.py`.
