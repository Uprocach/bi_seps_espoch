# Especificación: Profundización Arquitectónica y Desacoplamiento Integral (ESPOCH-DI-060)

## 1. Visión General
Esta especificación formaliza la refactorización arquitectónica profunda del Sistema de Indicadores Financieros SFPS (ESPOCH-DI-060), abordando de manera coordinada las 4 oportunidades de profundización identificadas y acordadas durante la sesión de arquitectura:

1. **Candidato 1 (Motor Analítico):** Consolidación de DuckDB y consultas Parquet en un módulo profundo (`AnalyticsRepository`), con extracción de renderizado binario en `ExportFormatter`.
2. **Candidato 4 (Dominio & Contrato):** Erradicación de la nomenclatura comercial "Pro" y rutas alias pasantes, formalizando el router `/api/v1/supervision` en el contrato OpenAPI 3.1.0 (`contracts/openapi.yaml`) conforme a ADR-0004 y GLOSSARY.md.
3. **Candidato 3 (Pipeline & Staging):** Aislamiento del orquestador del pipeline sin mutaciones de `os.environ["MART_DIR"]` y sustitución de la invocación web de `unittest` por una función de verificación pura `verify_mart_integrity()`.
4. **Candidato 2 (Frontend React):** Unificación del cliente HTTP (`httpClient.ts`) con soporte nativo de cookies HttpOnly (ADR-0001), centralización de estado de filtros y navegación en Zustand (`useDashboardStore`), y suscripción directa de vistas mediante TanStack Query, reduciendo `App.tsx` a un cascarón limpio de navegación (< 100 líneas).

---

## 2. Decisiones de Diseño y Límites de Módulos

### 2.1 Fase 1: Backend & Motor Analítico
- **Módulo Profundo `AnalyticsRepository`:**
  - Gestiona internamente un único pool multihilo de conexiones DuckDB (`threads=4`).
  - Centraliza el acceso y las consultas optimizadas a los cubos Parquet Hive (`fct_indicators_*`, `dim_entities`, `dim_segments`, `dim_provinces`).
  - Implementa:
    - `get_metadata_filters()`
    - `list_entities(params)`
    - `get_entity_by_ruc(ruc)`
    - `get_indicator_series(indicator, level, ...)`
    - `compare_entities(entity_ids, start_date, end_date, camel_dimension)` (absorbiendo `BenchmarkingService`)
    - `extract_entity_microdata(entity_ids, start_date, end_date)` (para exportación masiva)
- **Adaptador `ExportFormatter` (`backend/app/services/export_formatter.py`):**
  - Recibe datos estructurados de `AnalyticsRepository` y los serializa a streaming CSV (BOM UTF-8) o libros de trabajo Excel con formato visual regulatorio mediante `xlsxwriter`. No tiene dependencias de DuckDB ni rutas Parquet.
- **Router `/api/v1/supervision` (`backend/app/api/v1/supervision.py`):**
  - Sustituye a `backend/app/api/v1/pro.py`.
  - Expone:
    - `POST /api/v1/supervision/benchmarking/compare`
    - `POST /api/v1/supervision/export/csv`
    - `POST /api/v1/supervision/export/excel`
  - Se eliminan endpoints alias pasantes (`/compare` y `/indicators/benchmark-matrix`).
  - Se formalizan las rutas en `contracts/openapi.yaml` y se valida con `npm run contract:lint` (Spectral).

### 2.2 Fase 2: Pipeline de Datos & Staging
- **Parámetros Explícitos de Directorio:**
  - `build_marts(target_dir: Path)` y `verify_mart_integrity(target_dir: Path)` reciben explícitamente el directorio objetivo sin depender de `os.environ["MART_DIR"]`.
- **Verificación Pura del Gatekeeper:**
  - `etl/monthly_pipeline.py` implementa `verify_mart_integrity(target_dir: Path) -> ValidationReport`, que ejecuta aserciones analíticas directamente sobre DuckDB sin invocar `unittest.TestLoader().discover()`.
  - El resultado de la verificación se audita en la tabla forense `audit_logs` de SQLite vía `user_db_service`.
  - La suite de desarrollo existente (`test_marts.py`) se preserva para el comando manual `npm run etl:test`.

### 2.3 Fase 3: Frontend React
- **Store Ligero de Filtros y Navegación (`useDashboardStore`):**
  - Gestiona `activeView`, filtros globales (`selectedIndicator`, `level`, `selectedSegments`, `selectedProvince`, `fromPeriod`, `toPeriod`, `selectedRucs`) y búsqueda de entidades.
- **Cliente HTTP Profundo (`frontend/src/services/httpClient.ts`):**
  - Unifica `apiClient.ts` y el eliminado `proClient.ts`.
  - Consume endpoints canónicos `/api/v1/*` y `/api/v1/supervision/*`.
  - Manejo transparente de sesión HttpOnly (`credentials: "include"`), con tipado estricto generado de OpenAPI y parseo de errores RFC 9457.
- **Suscripción Reactiva vía TanStack Query:**
  - Hooks especializados: `useMetadataFiltersQuery`, `useIndicatorSeriesQuery`, `useEntitiesQuery`, `useBenchmarkingCompareQuery`.
  - Cada vista (`DashboardView`, `EntitiesView`, `BenchmarkingView`) invoca sus hooks directamente.
- **Adelgazamiento de `App.tsx`:**
  - Se eliminan ~250 líneas de `useState`, `useEffect` y prop-drilling.
  - `App.tsx` queda como un orquestador visual ligero (< 100 líneas) con `TopBar`, `Sidebar`, modales de autenticación y renderizado condicional de vistas.

---

## 3. Criterios de Éxito y Verificación Integral
1. `npm run contract:lint`: Cero errores de Spectral en `contracts/openapi.yaml`.
2. `npm run etl:test`: 100% de tests analíticos DuckDB aprobados.
3. `npm run backend:test`: 100% de tests de Pytest aprobados (incluyendo nuevas pruebas de supervisión e integridad).
4. `npm run frontend:build`: Compilación Vite + TypeScript exitosa sin advertencias de tipos.
5. `npm run test`: Suite integral de integración pasando al 100%.
