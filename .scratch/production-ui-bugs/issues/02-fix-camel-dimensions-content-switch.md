# Ticket 02: Reactividad de Contenido al Filtrar por Dimensiones CAMEL

**Status:** resolved  
**Tipo:** Bugfix / Feature Refinement  
**Blocked by:** 01  

---

## Resolución
1. En `frontend/src/store/useDashboardStore.ts`:
   - `setSelectedDimension(dim)` ahora conmuta automáticamente `selectedIndicator` al ratio representativo de dicha dimensión (`calidad_de_activos` -> `morosidad_cartera_total`, `capital` -> `solvencia_patrimonial`, `rentabilidad` -> `roa`, `liquidez` -> `liquidez_inmediata`, `manejo_administrativo` -> `eficiencia_operativa`).
2. En `frontend/src/components/views/DashboardView.tsx`:
   - Cuando `selectedDimension === "all"`, se mantienen las 5 tarjetas transversales de `KPICards`.
   - Cuando `selectedDimension !== "all"`, se despliega una galería interactiva completa con todos los ratios de la dimensión seleccionada (`dimAllIndicators`). Cada ratio muestra su número de ficha SEPS, nombre, descripción, polaridad normativa, unidad (`$`, `ratio` o `%`), valor actual y badge de acreditación con icono de candado.
   - Al hacer clic en cualquier tarjeta de la dimensión, se activa inmediatamente como `selectedIndicator` y proyecta su evolución histórica en `TimeSeriesChart`.
3. Verificado con `npm run frontend:build` y suite completa de pruebas.  

---

## Descripción del Problema
Cuando el usuario selecciona una dimensión CAMEL en el sidebar ("Calidad de Activos", "Rentabilidad", "Capital", "Liquidez", "Manejo Administrativo"):
1. Solo se actualiza el título del dashboard.
2. Las 5 tarjetas KPI superiores muestran siempre las mismas 5 métricas generales (morosidad, solvencia, roa, liquidez, eficiencia).
3. El gráfico `TimeSeriesChart` sigue proyectando el indicador global seleccionado previamente (e.g. `morosidad_cartera_total`).
4. No existe una interfaz para que el usuario explore y visualice los demás indicadores pertenecientes a la dimensión elegida (por ejemplo, las 17 fichas de Rentabilidad o las 28 de Calidad de Activos).

## Criterios de Aceptación
1. **Sincronización de Indicador por Defecto al Cambiar Dimensión:**
   - Al seleccionar una dimensión específica, el indicador activo debe conmutar automáticamente al ratio insignia de esa dimensión:
     - `calidad_de_activos` -> `morosidad_cartera_total`
     - `capital` -> `solvencia_patrimonial`
     - `rentabilidad` -> `roa`
     - `liquidez` -> `liquidez_inmediata`
     - `manejo_administrativo` -> `eficiencia_operativa`
2. **Explorador / Galería de Ratios de la Dimensión Seleccionada:**
   - En `DashboardView.tsx`, cuando `selectedDimension !== "all"`, debe desplegarse una galería o lista interactiva de todos los indicadores pertenecientes a esa dimensión (procedentes de `EXTENDED_CATALOG`).
   - Cada tarjeta/ítem debe mostrar: Número de Ficha SEPS, Nombre del indicador, descripción resumida, polaridad normativa y badge de acceso público / acreditado.
   - Al hacer clic en cualquier indicador de la dimensión, éste debe activarse como `selectedIndicator` y cargar inmediatamente su serie histórica en `TimeSeriesChart`.
   - Si el usuario no está acreditado y el indicador requiere acreditación, debe mostrar una insignia de candado o solicitar acceso institucional.
3. **Restauración al modo global ("all"):**
   - Si se selecciona la vista global 360° ("all"), el dashboard regresa a la vista de los 5 indicadores transversales CAMEL estándar.
4. **Verificación:**
   - `npm run test` debe aprobar el 100% de las pruebas (Spectral, DuckDB, Pytest y build de Vite).
