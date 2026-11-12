# ADR-0006: Despliegue Serverless Zero-Cost con Vercel, Supabase y GitHub Actions

## Estado
Aceptado

## Contexto
El proyecto ESPOCH-DI-060 requería un cambio de paradigma en infraestructura: prescindir de servidores dedicados de pago (VPS o instancias fijas) y migrar la plataforma completa a un modelo de costo cero ($0 USD) perpetuo, manteniendo:
1. El contrato OpenAPI 3.1.0 inalterado.
2. El motor analítico DuckDB operando sobre cubos multidimensionales Parquet.
3. La gobernanza de acceso institucional RBAC con sesiones mediante cookies seguras `HttpOnly`.
4. El padrón de usuarios y la trazabilidad de auditoría forense con persistencia transaccional duradera (evitando pérdida de datos por reinicios o contenedores efímeros).
5. La sincronización periódica mensual con el portal de estadísticas de la SEPS sin exceder tiempos de espera de funciones serverless.

## Decisiones Arquitectónicas

1. **Frontend en Vercel (Static SPA):**
   - El código React 18 + Vite + Tailwind se compila y aloja en el CDN perimetral de Vercel.
   - El enrutamiento hacia la API analítica se realiza bajo el mismo origen (`/api/v1/*`), evitando problemas de CORS y asegurando compatibilidad nativa con cookies `HttpOnly` y `SameSite`.

2. **Backend Serverless en Vercel Functions (`/api`):**
   - FastAPI se expone a través de una Vercel Function en `api/index.py`.
   - Los cubos Parquet (`data/processed/mart/`, con un tamaño total auditado de 22.7 MB) se empaquetan directamente en el bundle de despliegue.
   - DuckDB se ejecuta embebido en memoria dentro del micro-contenedor serverless, ejecutando consultas analíticas de lectura local en 5–15 ms con cero costo de transferencia de datos.

3. **Persistencia Transaccional en Supabase (PostgreSQL Gestionado):**
   - El padrón de usuarios institucionales (`users`) y la bitácora de auditoría forense (`audit_logs`) migran de SQLite a PostgreSQL en Supabase (capa gratuita de 500 MB).
   - Se implementa una capa de acceso a datos dual: si la variable de entorno `DATABASE_URL` está presente, el sistema se conecta a Supabase PostgreSQL; si está ausente, opera con fallback transparente a SQLite local (`data/users.db`), garantizando la ejecución ininterrumpida de tests unitarios (`pytest`) y desarrollo offline.
   - Las tablas y el usuario administrador inicial se auto-inicializan de forma idempotente en el ciclo de vida (`lifespan`) de FastAPI.

4. **Automatización ETL y Web Scraping en GitHub Actions:**
   - La ingesta periódica de balances y patrimonio técnico SEPS se delega a un workflow programado en GitHub Actions (`.github/workflows/monthly-etl.yml`).
   - El cron se programa para ejecutarse los días **18 y 25 de cada mes a las 03:00 UTC**, coincidiendo con la ventana habitual de publicación de la Dirección Nacional de Estadísticas de la SEPS.
   - Cuenta con disparador manual (`workflow_dispatch`).
   - El workflow ejecuta `etl/monthly_pipeline.py`, valida los datos con `verify_mart_integrity()` y, solo si las 7 aserciones matemáticas e integridad Parquet son aprobadas, confirma los cambios a la rama `master`, desencadenando un despliegue atómico en Vercel.

## Consecuencias

### Positivas
- **Costo $0:** Todos los servicios (Vercel, Supabase, GitHub Actions) operan dentro de sus niveles gratuitos perpetuos.
- **Rendimiento:** Las consultas analíticas continúan resolviéndose en memoria local con DuckDB (< 20 ms).
- **Mantenibilidad:** Cero gestión de parches de sistema operativo, firewalls o procesos daemon que se caigan.
- **Seguridad:** Cookies `HttpOnly` bajo el mismo dominio de producción en Vercel.

### Negativas / Mitigaciones
- **Límite de Ejecución Serverless:** Resuelto delegando el crawler y ETL de larga duración a GitHub Actions en lugar de Vercel Functions.
- **Supabase Inactivity Pausing:** En la capa gratuita, los proyectos de Supabase pueden pausarse tras 7 días de inactividad total. Mitigado por el tráfico constante del sistema y el cron quincenal de GitHub Actions que realiza pings de conexión.
