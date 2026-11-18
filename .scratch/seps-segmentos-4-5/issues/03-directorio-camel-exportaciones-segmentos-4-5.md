# 03: Directorio, Diagnóstico CAMEL (Sin dato) y Exportaciones para Segmentos 4 y 5 (Acceso Institucional)

**What to build:** En el Acceso Institucional Acreditado, los usuarios pueden buscar y filtrar cooperativas activas de Segmentos 4 y 5 en el Directorio, compararlas en el semáforo y benchmarking CAMEL contra la línea base del Segmento 1 en cortes trimestrales viendo un badge neutral `Sin dato` en indicadores en `null` (como Liquidez Ficha 52 y Solvencia Ficha 62) sin que generen falsas alertas, y exportar sus microdatos históricos trimestrales en CSV y Excel.

**Blocked by:** 02: Cubos analíticos, API y Dashboard Macro para Segmentos 4 y 5 (Trimestral, EC y nulidad CUC)

**Status:** done

- [x] El Directorio de entidades lista cooperativas activas de `SEGMENTO_4` y `SEGMENTO_5` y permite filtrarlas por segmento y provincia.
- [x] El endpoint y la vista de Diagnóstico CAMEL manejan valores `null` sin errores, muestran un estado neutral (`Sin dato`) para las fichas ausentes (CUC 6 dígitos / Patrimonio Técnico) y las excluyen del conteo de alertas regulatorias.
- [x] Las exportaciones en CSV y Excel incluyen correctamente los registros trimestrales de cooperativas de Segmentos 4 y 5.
- [x] Pruebas en Backend y Frontend verifican la tolerancia a `null` en CAMEL, la visualización del badge neutral y la exportación.
