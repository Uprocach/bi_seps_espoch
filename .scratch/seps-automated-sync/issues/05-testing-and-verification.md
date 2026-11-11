# Ticket 05: Suite de Pruebas y Certificación Final

Status: ready-for-agent
Blocked by: 04

## Descripción
Implementar suite de pruebas Pytest en `backend/tests/test_seps_sync.py`:
- Prueba de endpoints con roles RBAC (401 sin auth, 403 para investigador/auditor, 200/202 para admin).
- Simulación de ciclo de sincronización con mock y validación del estado en vivo.
- Ejecución de `npm run test` (Spectral + DuckDB ETL + Pytest + Frontend build).

## Criterios de Aceptación
1. 100% de tests aprobados.
2. Cero advertencias de contrato.
3. Commit registrado en Git.
