# Especificación Técnica: Despliegue Serverless Zero-Cost (Vercel + Supabase + GitHub Actions)

## 1. Visión y Objetivos
Migrar la plataforma analítica de indicadores SFPS (ESPOCH-DI-060) a una arquitectura serverless de costo perpetuo cero ($0 USD), garantizando:
- Contrato OpenAPI 3.1.0 inalterado.
- Motor DuckDB embebido en Vercel Functions resolviendo consultas sobre 22.7 MB de Parquet en < 20 ms.
- Persistencia institucional de usuarios y auditoría forense en PostgreSQL gestionado (Supabase).
- Automatización del pipeline mensual de la SEPS mediante GitHub Actions con validación matemática estricta.

## 2. Componentes y Arquitectura

### 2.1 Backend: Persistencia Dual (PostgreSQL / SQLite)
- Módulos afectados: `backend/app/services/user_db_service.py` y `backend/app/services/audit_service.py`.
- Lógica de conexión:
  - Si `settings.DATABASE_URL` comienza con `postgres://` o `postgresql://`, se utiliza conexión `psycopg`.
  - Si `settings.DATABASE_URL` no está definida o es `sqlite://`, se utiliza fallback transparente a `sqlite3` local (`data/users.db`).
- Tablas auto-gestionadas de forma idempotente: `users` y `audit_logs`.
- Siembra automática del usuario `admin` inicial si la tabla `users` está vacía.

### 2.2 Vercel Monorepo Packaging
- Archivo raíz `vercel.json`:
  - Enrutamiento: `/api/(.*)` hacia `api/index.py`.
  - Enrutamiento estático: todas las demás rutas hacia los archivos estáticos en `frontend/dist`.
- Punto de entrada `api/index.py`:
  - Importa `backend.app.main:app` para ser ejecutada por el runtime Python de Vercel.
- Los cubos Parquet en `data/processed/mart/` se incluyen en el despliegue de Vercel.

### 2.3 Orquestación ETL en GitHub Actions
- Archivo `.github/workflows/monthly-etl.yml`:
  - Cron: `0 3 18,25 * *` (Días 18 y 25 a las 03:00 UTC).
  - Manual: `workflow_dispatch`.
  - Pasos:
    1. Checkout del repositorio.
    2. Setup de Python 3.12.
    3. Instalación de dependencias de `requirements.txt`.
    4. Ejecución de `etl/monthly_pipeline.py`.
    5. Validación obligatoria de integridad con `etl/test_marts.py` (`verify_mart_integrity`).
    6. Commit atómico y push a `master` si se generaron nuevos datos verificados.

## 3. Plan de Verificación y Criterios de Aceptación
1. `npm run contract:lint` aprueba sin advertencias ni errores.
2. `npm run backend:test` aprueba 100% de tests en modo SQLite local.
3. Se agrega test unitario que valide la resolución de PostgreSQL cuando `DATABASE_URL` está configurada.
4. `npm run frontend:build` compila sin errores TypeScript.
5. `npm run test` aprueba la suite integral.
