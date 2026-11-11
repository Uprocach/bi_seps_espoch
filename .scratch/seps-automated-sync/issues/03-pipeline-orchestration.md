# Ticket 03: Orquestación de Pipeline y Endpoints Asíncronos

Status: ready-for-agent
Blocked by: 02

## Descripción
1. Agregar bandera `--sync-web` en `etl/monthly_pipeline.py`.
2. Implementar los endpoints `POST /api/v1/admin/pipeline-sync` y `GET /api/v1/admin/pipeline-sync-status` en `backend/app/api/v1/admin_pipeline.py` utilizando `FastAPI BackgroundTasks`.
3. Manejo de estados: `idle`, `downloading`, `extracting`, `validating`, `success`, `failed`.
4. Registro en `audit_logs` del resultado de la sincronización.

## Criterios de Aceptación
1. Petición POST responde `202 Accepted` de inmediato en modo asíncrono.
2. Consulta GET refleja el estado y porcentaje de avance.
3. Rol `administrador` requerido; roles no autorizados reciben 401/403.
