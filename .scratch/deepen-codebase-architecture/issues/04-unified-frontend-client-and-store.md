# Ticket 04: Cliente HTTP Profundo y Store de Filtros/Navegación

Status: resolved
Blocked by: none (02 resuelto)

## Descripción
1. Implementar `frontend/src/services/httpClient.ts` unificando `apiClient.ts` y eliminando `proClient.ts`:
   - Configurado con `credentials: "include"` para sesión HttpOnly nativa (ADR-0001).
   - Eliminación de tokens Bearer en memoria muertos (`inMemoryToken`, `setAuthToken`).
   - Métodos tipados para `/api/v1/metadata/filters`, `/api/v1/entities`, `/api/v1/indicators/series`, `/api/v1/supervision/benchmarking/compare`, `/api/v1/supervision/export/*`, `/api/v1/admin/*`.
   - Manejo centralizado de errores RFC 9457 (`application/problem+json`).
2. Crear `frontend/src/store/useDashboardStore.ts` con Zustand:
   - Estado de navegación: `activeView` (`dashboard`, `entities`, `benchmarking`, `catalog`, `admin_users`, `audit_logs`).
   - Estado de filtros: `selectedIndicator`, `level`, `selectedSegments`, `selectedProvince`, `fromPeriod`, `toPeriod`, `selectedRucs`, `searchQuery`, `entityPage`.
   - Acciones atómicas: `setActiveView`, `setSelectedIndicator`, `setFilterRange`, `toggleRuc`, `setSearchQuery`.

## Criterios de Aceptación
1. `proClient.ts` y `apiClient.ts` unificados delegando hacia `httpClient.ts`.
2. `httpClient.ts` maneja todas las llamadas de red con soporte transparente de cookies y tipos OpenAPI.
3. `useDashboardStore` almacena y sincroniza el estado de visualización sin prop drilling.

## Resolución
- Creado `frontend/src/services/httpClient.ts` con manejo nativo de cookies HttpOnly y tipado estricto OpenAPI.
- `frontend/src/services/apiClient.ts` y `proClient.ts` convertidos en adaptadores de compatibilidad transparentes.
- Creado `frontend/src/store/useDashboardStore.ts` con Zustand para gobernar filtros y navegación.
- Compilación frontend y linting de contrato verificados con 100% de éxito.
