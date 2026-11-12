# Ticket 05: Desacoplamiento de Vistas con TanStack Query y Adelgazamiento de App.tsx

Status: resolved
Blocked by: 04

## Descripción
1. Crear hooks reactivos en `frontend/src/hooks/useIndicatorsQueries.ts` con TanStack Query:
   - `useMetadataFilters()`
   - `useIndicatorSeries()`
   - `useEntitiesList()`
   - `useBenchmarkingCompare()`
2. Refactorizar las vistas:
   - `frontend/src/components/views/DashboardView.tsx`: consume series y filtros directamente del store y queries.
   - `frontend/src/components/views/EntitiesView.tsx`: consume lista de entidades directamente del store y queries.
   - `frontend/src/components/views/BenchmarkingView.tsx` (renombrar o reubicar desde `frontend/src/components/pro/BenchmarkingProView.tsx`): consume comparación CAMEL directamente.
3. Adelgazar `frontend/src/App.tsx`:
   - Eliminar los 15 `useState` de datos y filtros, las funciones pasantes y el prop drilling masivo.
   - Mantener exclusivamente el envoltorio de `QueryClientProvider`, `Sidebar`, `TopBar`, modales y el renderizado condicional de vistas según `activeView`.
   - Reducir `App.tsx` a menos de 100 líneas limpias.

## Criterios de Aceptación
1. `App.tsx` tiene menos de 120 líneas de código y cero prop-drilling hacia vistas.
2. Todas las vistas obtienen sus datos directamente mediante hooks de TanStack Query y el store de Zustand.
3. Se elimina la carpeta `frontend/src/components/pro/` en concordancia con ADR-0004.
