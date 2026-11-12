# Ticket 06: Verificación y Certificación Full-Stack

Status: resolved
Blocked by: 03, 05

## Descripción
Ejecutar la suite completa de pruebas y auditoría técnica:
1. `npm run contract:lint` (Spectral) sobre `contracts/openapi.yaml`.
2. `npm run etl:test` (Suite de pruebas analíticas DuckDB sobre cubos Parquet).
3. `npm run backend:test` (Suite de pruebas Pytest, actualizando pruebas que referenciaban `/api/v1/pro/` hacia `/api/v1/supervision/`).
4. `npm run frontend:build` (Compilación TypeScript + Vite sin errores de tipo ni de importación).
5. `npm run test` (Suite integral end-to-end).
6. Registro de commits estructurados en Git.

## Criterios de Aceptación
1. 100% de tests de contrato, backend, ETL y frontend aprobados.
2. Cero advertencias de TypeScript.
3. El árbol de trabajo de Git queda limpio y con commits atómicos por hito.
