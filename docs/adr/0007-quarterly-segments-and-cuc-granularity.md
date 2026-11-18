# ADR-0007: Integración de Segmentos Trimestrales (4 y 5) y Granularidad CUC

## Estado
Aceptado

## Contexto
La SEPS publica las bases de datos de **Estados Financieros Mensuales** (CUC a 6 dígitos) únicamente para los Segmentos 1, 2, 3, Mutualistas, FINANCOOP y CONAFIPS. Las cooperativas de **Segmento 4 y Segmento 5** se publican de forma separada bajo **Estados Financieros Trimestrales** (cortes `03`, `06`, `09` y `12`), con una granularidad máxima de **4 dígitos** en el Catálogo Único de Cuentas (CUC) y sin reportes de Patrimonio Técnico / ACPR.

Integrar estos segmentos en el sistema requiere resolver tres compromisos de diseño:
1. Cómo evitar distorsiones temporales en la serie mensual nacional (`EC`) al combinar segmentos mensuales y trimestrales.
2. Cómo tratar indicadores cuyas fórmulas oficiales (Fichas Metodológicas V3.0) exigen subcuentas de 6 dígitos ausentes en las bases trimestrales.
3. Cómo determinar si una cooperativa trimestral está activa cuando los datos mensuales avanzan entre cierres de trimestre.

## Decisiones

1. **Fuente exclusiva de Bases de Datos Trimestrales (2018–2026) filtrada a Segmentos 4 y 5:**
   - El crawler y ETL ingieren únicamente las *Bases de Datos* de `Estados Financieros Trimestrales` (`.txt`/`.csv` tabulados, soportando variantes históricas de columnas), descartando los boletines `.xlsm`.
   - En las bases trimestrales históricas (2018–2025) que también incluyen Segmentos 1–3 a 4 dígitos, se filtran exclusivamente `SEGMENTO 4` y `SEGMENTO 5` para no duplicar ni degradar la información mensual a 6 dígitos de los Segmentos 1–3.

2. **Exclusión de Segmentos Trimestrales del Agregado Nacional Mensual (`EC`):**
   - `fct_indicators_country_monthly` (`level=country`, clave `EC`) agrega por *Ratio de Sumas* exclusivamente a los segmentos de reporte mensual (`SEGMENTO_1`, `SEGMENTO_1_MUTUALISTA`, `SEGMENTO_2`, `SEGMENTO_3`).
   - **Alternativas descartadas:**
     - *Sumar Segmentos 4 y 5 en los meses de cierre (`03, 06, 09, 12`):* generaría saltos artificiales (efecto sierra) en volúmenes totales y conteo de entidades cada tres meses.
     - *Carry-forward (arrastre del último trimestre a los meses intermedios):* mezclaría saldos contables de distintas fechas de corte en un mismo periodo mensual.
   - Los Segmentos 4 y 5 se consultan y comparan a nivel de segmento y cooperativa individual.

3. **Nulidad Estricta (`NULL`) ante Ausencia de Subcuentas CUC de 6 Dígitos o Patrimonio Técnico:**
   - Los indicadores que requieren subcuentas de 6 dígitos no publicadas en las bases trimestrales —**Ficha 52 (`liquidez_inmediata`: `210305`, `210310`)**, **Fichas 19–27 (`1499xx`)** y **Fichas 39–50 (`5104xx`)**— así como las **Fichas 58–63** de Patrimonio Técnico se mantienen en `NULL` para Segmentos 4 y 5.
   - **Alternativa descartada:** Aproximar la Ficha 52 usando la cuenta padre de 4 dígitos (`2103`), lo cual incluiría depósitos a más de 90 días y violaría la definición normativa de la Ficha Metodológica V3.0.
   - En el diagnóstico/semáforo CAMEL, los indicadores en `NULL` se muestran con un estado neutral (`Sin dato`) y no penalizan el conteo de alertas.

4. **Evaluación de `dim_entities.is_active` por Frecuencia de Segmento:**
   - Una entidad se considera activa si su último periodo reportado coincide con el máximo periodo disponible de su propia frecuencia (`monthly` vs. `quarterly`), evitando que las entidades de Segmentos 4 y 5 aparezcan inactivas cuando los datos mensuales de Segmentos 1–3 avanzan entre trimestres.

## Consecuencias

### Positivas
- **Integridad estadística:** La serie mensual país (`EC`) mantiene continuidad sin saltos artificiales ni mezcla de fechas de corte.
- **Fidelidad normativa:** Ningún indicador se calcula con aproximaciones fuera de la Ficha Metodológica V3.0 de la SEPS.
- **Trazabilidad UI:** El contrato OpenAPI (`Segment.reporting_frequency`) ya permite distinguir `monthly` vs. `quarterly` en filtros y vistas.

### Negativas / Mitigaciones
- **Menor cobertura de indicadores en Segmentos 4 y 5:** Liquidez Inmediata (Ficha 52) y Solvencia Regulatoria (Ficha 62) no estarán disponibles para estos segmentos; se mitiga mostrando `Sin dato` en la UI y manteniendo disponible Ficha 1 (*Solvencia Patrimonial*, calculada a 1 dígito).
