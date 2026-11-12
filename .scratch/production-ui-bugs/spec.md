# Especificación: Corrección de Fallos Críticos de Interfaz en Producción

**ID del Esfuerzo:** `production-ui-bugs`  
**Estado:** `ready-for-agent`  
**Fecha:** 2026-11-12  
**Origen:** Reporte de Usuario en Entorno de Producción (Vercel)

---

## 1. Contexto & Diagnóstico del Problema

### Bug 1: Contenido de la pantalla queda por debajo del Sidebar (Overlay Involuntario)
- **Síntoma:** En resoluciones de escritorio (pantalla completa o mediana), todo el contenido principal de la aplicación (`TopBar`, tarjetas KPI, gráficos, tablas y pie de página) se renderiza detrás/por debajo del menú lateral `Sidebar`, sin importar si el sidebar está abierto (`w-72`) o colapsado (`w-20`).
- **Causa Raíz:** En `Sidebar.tsx`, el elemento `<aside>` está posicionado de forma fija (`fixed top-0 bottom-0 left-0 z-50 w-72 lg:translate-x-0`). En `App.tsx`, el contenedor principal de la vista (`<div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">`) carece de un margen/padding izquierdo compensatorio (`lg:pl-72` / `lg:pl-20`). Al ser `fixed`, el sidebar se superpone directamente sobre los primeros 288px (u 80px) del contenido.
- **Solución Requerida:** Aplicar desplazamiento dinámico condicional en el contenedor principal de `App.tsx` según el estado `isSidebarCollapsed` (`lg:pl-72` cuando está expandido, `lg:pl-20` cuando está colapsado), manteniendo `pl-0` en pantallas móviles.

### Bug 2: Dimensiones CAMEL no cambian el contenido, solo los títulos
- **Síntoma:** Al hacer clic en cualquiera de las 5 dimensiones CAMEL en el sidebar ("Calidad de Activos", "Rentabilidad", "Capital", "Liquidez", "Manejo Administrativo"), la pantalla solo altera el título superior, pero las 5 tarjetas KPI, la serie histórica y el resto del dashboard permanecen inmutables mostrando siempre los valores por defecto globales (`morosidad_cartera_total`).
- **Causa Raíz:**
  1. En `DashboardView.tsx`, `KPICards` siempre consume la constante estática `CORE_5_INDICATORS` (1 indicador fijo por dimensión), independientemente de la dimensión seleccionada.
  2. `selectedIndicator` nunca se actualiza al cambiar `selectedDimension`, quedando anclado en `morosidad_cartera_total` incluso al ingresar a dimensiones como "Rentabilidad" o "Liquidez".
  3. Los indicadores específicos filtrados por dimensión (`dimAllIndicators`) solo se empleaban para contabilizar una insignia numérica en la cabecera, sin mostrar un selector, cuadrícula o lista interactiva que permita al usuario examinar y alternar entre los ratios de esa dimensión.
- **Solución Requerida:**
  1. Cuando `selectedDimension !== "all"`, sincronizar automáticamente `selectedIndicator` con el indicador primario de dicha dimensión (ej. `rentabilidad` -> `roa`, `capital` -> `solvencia_patrimonial`, `liquidez` -> `liquidez_inmediata`, `calidad_de_activos` -> `morosidad_cartera_total`, `manejo_administrativo` -> `eficiencia_operativa`).
  2. En `DashboardView.tsx`, cuando se selecciona una dimensión específica, renderizar un selector / galería interactiva de todos los indicadores pertenecientes a esa dimensión (organizados por nivel de acceso público y acreditado), permitiendo al usuario hacer clic en cualquiera de ellos para proyectar su serie histórica en `TimeSeriesChart`.
  3. En `KPICards`, adaptar la visualización para destacar la dimensión activa o mostrar las métricas representativas de dicha dimensión.

---

## 2. Tickets de Implementación

1. `01-fix-sidebar-overlay-layout.md`: Ajustar compensación de layout en `App.tsx` para eliminar la superposición del sidebar.
2. `02-fix-camel-dimensions-content-switch.md`: Implementar reactividad completa y catálogo interactivo de indicadores por dimensión CAMEL en `DashboardView.tsx` y `useDashboardStore.ts`.
