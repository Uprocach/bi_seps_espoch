# Especificación Técnica: Ingesta Automatizada y Sincronización Web SEPS

- **Feature:** `seps-automated-sync`
- **Estado:** Aprobado
- **Fecha:** 2026-11-11
- **Autor:** Pair Programming ESPOCH-DI-060 / Antigravity

---

## 1. Objetivo y Alcance

Automatizar la descarga, extracción y procesamiento de boletines mensuales de estados financieros (B11) y patrimonio técnico (ACPR) directamente desde el portal oficial de estadísticas de la SEPS (`https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/`), eliminando la necesidad de incorporar manualmente los archivos al repositorio.

El flujo se integra de forma nativa con la **Fase 2 (Zero-Downtime Parquet Switch)**, garantizando que los datos descargados pasen por staging y validación matemática estricta antes de impactar el entorno de producción.

---

## 2. Flujo Arquitectónico End-to-End

```
                           FLUJO DE SINCRONIZACIÓN AUTOMATIZADA
  
  [Portal SEPS: estadisticas.seps.gob.ec]
                 │
                 ▼
  ┌──────────────────────────────┐
  │ 1. Crawler / Extractor Web   │
  │    (etl/seps_crawler.py)     │ ──> Inspecciona WordPress Simple Download Monitor
  │                              │     Detecta si hay periodo > latest_period del sistema.
  └──────────────┬───────────────┘
                 ▼
  ┌──────────────────────────────┐
  │ 2. Descarga & Descompresión  │
  │    en Streaming              │ ──> Descarga ZIP, parsea libros de balance (.xlsm / TSV)
  │                              │     Genera Parquet canónico de 7 columnas en data/interim/
  └──────────────┬───────────────┘
                 ▼
  ┌──────────────────────────────┐
  │ 3. Pipeline Staging & Switch │
  │    (etl/monthly_pipeline.py) │ ──> Construye cubos en mart_staging/
  │                              │     Valida 100% de tests matemáticos (test_marts.py)
  │                              │     Ejecuta atomic_switch a producción
  └──────────────┬───────────────┘
                 ▼
  ┌──────────────────────────────┐
  │ 4. Notificación y Bitácora   │
  │    (audit_logs en users.db)  │ ──> Registra auditoría forense con bytes y periodo
  └──────────────────────────────┘
```

---

## 3. Contratos de API (OpenAPI 3.1.0)

Se agregan dos endpoints administrativos bajo el tag `Admin`:

1. `POST /api/v1/admin/pipeline-sync`:
   - Dispara la tarea de sincronización web con la SEPS.
   - Parámetros en body: `force: bool = false`, `dry_run: bool = false`.
   - Respuestas: `200 OK` (modo síncrono/dry-run) o `202 Accepted` (modo asíncrono con BackgroundTasks).

2. `GET /api/v1/admin/pipeline-sync-status`:
   - Retorna el estado en vivo de la última tarea de sincronización:
     - `idle`, `downloading`, `extracting`, `validating`, `success`, `failed`.
     - `progress_percent`: `0 - 100`.
     - `last_sync_timestamp`: ISO 8601.
     - `detected_period`: `YYYY-MM`.
     - `error_message`: `string | null`.

---

## 4. Componentes a Desarrollar

- **Crawler de Descargas (`etl/seps_crawler.py`):**
  - Consulta `https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/`.
  - Extrae enlaces de descarga `?sdm_process_download=1&download_id=...`.
  - Descomprime el ZIP en memoria, procesa libros de Excel macro (.xlsm) o texto tabular, mapea a columnas canónicas (`fecha_de_corte`, `segmento`, `ruc`, `razon_social`, `cuenta`, `descripcion_cuenta`, `saldo__usd_`).
- **Orquestador de Pipeline (`etl/monthly_pipeline.py`):**
  - Añadir soporte para `--sync-web`.
- **Backend API (`backend/app/api/v1/admin_pipeline.py`):**
  - Endpoints protegidos con rol `administrador`.
  - Manejador de estado de sincronización en memoria / persistente.
- **Frontend UI (`AdminUsersView.tsx` o componente dedicado):**
  - Tarjeta de control de sincronización SEPS en tiempo real con botón *"Sincronizar con Portal SEPS"* y estado de conexión.
- **Suite de Pruebas Pytest (`backend/tests/test_seps_crawler.py`):**
  - Pruebas unitarias con mocks HTTP y pruebas de integración.
