# Ticket 02: Punto de Entrada y Configuración de Vercel Monorepo

Status: resolved
Blocked by: 01

## Descripción
1. Crear el punto de entrada serverless `api/index.py`:
   - Configurar `sys.path` para importar correctamente el paquete `backend`.
   - Exponer la instancia `app` de FastAPI desde `backend.app.main:app`.
2. Crear el archivo de configuración raíz `vercel.json`:
   - Configurar builds para `api/index.py` con `@vercel/python`.
   - Configurar builds para el frontend con `@vercel/static-build` o comando de build `npm --prefix frontend run build` hacia `frontend/dist`.
   - Configurar rewrites: `/api/(.*)` -> `/api/index.py`, `/(.*)` -> `/frontend/dist/$1` o SPA fallback.
3. Asegurar que los cubos Parquet en `data/processed/mart/` queden incluidos en el empaquetado de la función serverless mediante la directiva `includeFiles` en `vercel.json`.

## Criterios de Aceptación
1. `vercel.json` es válido y sigue las directivas oficiales de Vercel para monorepos React + Python FastAPI.
2. `api/index.py` puede ser importado localmente sin errores de módulo.
3. El frontend y backend comparten el mismo origen `/api/v1` en producción.
