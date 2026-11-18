# 02: Cubos analíticos, API y Dashboard Macro para Segmentos 4 y 5 (Trimestral, EC y nulidad CUC)

**What to build:** El motor de construcción de cubos analíticos unifica la capa intermedia mensual (Segmentos 1–3 y Mutualistas) con la capa intermedia trimestral (Segmentos 4 y 5), expone los 6 segmentos con su `reporting_frequency` correcto (`quarterly` para 4 y 5), evalúa la condición de Entidad Activa según la frecuencia del segmento, mantiene el Agregado Nacional Mensual (`EC`) exclusivamente con segmentos mensuales (ADR-0007), y deja en `NULL` los indicadores dependientes de 6 dígitos CUC o Patrimonio Técnico. De extremo a extremo, los endpoints de metadatos y series y el Dashboard Macro (Acceso Abierto) permiten consultar las series históricas trimestrales de Segmento 4 y 5 con su distintivo `Trimestral` en los selectores.

**Blocked by:** 01: Ingesta y extracción histórica de Bases Trimestrales SEPS (Segmentos 4 y 5)

**Status:** done

- [x] La dimensión de segmentos registra `reporting_frequency = 'quarterly'` para `SEGMENTO_4` y `SEGMENTO_5` y `'monthly'` para los demás segmentos.
- [x] Los cubos analíticos de entidad y segmento incluyen las series trimestrales de `SEGMENTO_4` y `SEGMENTO_5` (cortes `03`, `06`, `09`, `12`) manteniendo en `NULL` las fichas de 6 dígitos (incluida Ficha 52 de Liquidez Inmediata, Fichas 19–27 y Fichas 39–50) y las Fichas 58–63 de Patrimonio Técnico.
- [x] El Agregado Nacional Mensual (`EC`) excluye los segmentos trimestrales para evitar saltos de sierra cada 3 meses.
- [x] El atributo de Entidad Activa (`is_active`) se calcula contra el último periodo disponible de la propia frecuencia del segmento, manteniendo activas a las cooperativas trimestrales cuando los datos mensuales avanzan entre trimestres.
- [x] Los endpoints de filtros y series devuelven `SEGMENTO_4` y `SEGMENTO_5` con su `reporting_frequency` y conteo de entidades activas, y los selectores del Dashboard Macro muestran un distintivo `Trimestral`.
- [x] Pruebas en las costuras ETL, Backend y Frontend verifican el comportamiento completo.
