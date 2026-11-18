# Especificación: Integración de Cooperativas de Segmento 4 y Segmento 5 (SEPS)

Status: ready-for-agent

---

## Problem Statement

El sistema actual únicamente ingesta y expone información financiera mensual de cooperativas de Segmentos 1, 2, 3 y Mutualistas de Segmento 1. Sin embargo, la SEPS también publica información oficial de las cooperativas de **Segmento 4** y **Segmento 5** en su portal de estadísticas bajo **Estados Financieros Trimestrales** (con periodicidad trimestral y catálogo contable CUC a 4 dígitos). Como resultado, analistas e investigadores no pueden consultar la evolución sectorial de estos dos segmentos ni incluir a sus ~184 cooperativas activas en el directorio institucional, el diagnóstico CAMEL o las exportaciones.

## Solution

Extender el pipeline de extracción y construcción de cubos analíticos para descubrir, descargar e ingestar las **Bases de Datos Trimestrales** de la SEPS (serie histórica 2018–2026), filtrando exclusivamente las entidades de `SEGMENTO 4` y `SEGMENTO 5` para no duplicar ni degradar la información mensual a 6 dígitos de los Segmentos 1–3.

A nivel analítico y de presentación:
- Se preserva la continuidad estadística del **Agregado Nacional Mensual (`EC`)** manteniéndolo exclusivamente con los segmentos de reporte mensual (`SEGMENTO_1`, `SEGMENTO_1_MUTUALISTA`, `SEGMENTO_2`, `SEGMENTO_3`).
- Se evalúa la condición de **Entidad Activa** respecto al último periodo disponible de la propia frecuencia de reporte del segmento (`monthly` vs. `quarterly`), evitando que las cooperativas de Segmentos 4 y 5 aparezcan inactivas entre cierres trimestrales.
- Se mantiene nulidad estricta (`NULL`) en los indicadores que exigen subcuentas CUC de 6 dígitos (Ficha 52 de Liquidez Inmediata, Fichas 19–27 y Fichas 39–50) o reportes de Patrimonio Técnico (Fichas 58–63), mostrándolos en el diagnóstico CAMEL con un estado neutral (`Sin dato`) que no penaliza el semáforo.
- Se expone la periodicidad trimestral (`reporting_frequency: quarterly`) en filtros y vistas de Acceso Abierto y Acceso Institucional Acreditado.

## User Stories

1. As an investigador del Acceso Abierto, I want to filter macro indicator series by `SEGMENTO_4` and `SEGMENTO_5`, so that I can analyze the historical quarterly evolution of smaller credit unions in Ecuador.
2. As an investigador del Acceso Abierto, I want to see a clear indicator that `SEGMENTO_4` and `SEGMENTO_5` report quarterly (`Trimestral`), so that I understand why their data points appear only in March, June, September, and December.
3. As an investigador del Acceso Abierto, I want the national monthly aggregate (`EC`) to remain free of artificial quarterly jumps, so that month-over-month macro trends are not distorted by ~184 entities appearing only every three months.
4. As an investigador acreditado, I want to search and filter `SEGMENTO_4` and `SEGMENTO_5` cooperatives in the Entity Directory, so that I can inspect their individual profiles and active status.
5. As an investigador acreditado, I want `SEGMENTO_4` and `SEGMENTO_5` cooperatives to remain marked as active between quarterly cutoffs when monthly segments advance ahead, so that they do not disappear from active entity filters.
6. As an investigador acreditado, I want to include `SEGMENTO_4` and `SEGMENTO_5` cooperatives in the CAMEL benchmarking comparator against Segmento 1 baselines on quarterly cutoff periods, so that I can evaluate their capital, asset quality, management, and earnings.
7. As an investigador acreditado, I want missing 6-digit CUC and Patrimonio Técnico indicators (such as Liquidez Inmediata Ficha 52 and Solvencia Ficha 62) to display as neutral "Sin dato" rather than failing or triggering red alerts, so that Segmento 4 and 5 entities are not unfairly penalized.
8. As an investigador acreditado or auditor, I want to export historical quarterly microdata and CAMEL diagnostics for `SEGMENTO_4` and `SEGMENTO_5` entities in CSV and Excel, so that I can perform offline analysis.
9. As an operador del sistema, I want the automated SEPS crawler to discover and download both monthly and quarterly database archives (including historical `.csv` and `SALDO(USD)` schema variants from 2018–2026), so that Segmento 4 and 5 data stays synchronized automatically without manual intervention.
10. As an operador del sistema, I want the ETL pipeline to filter quarterly archives strictly to `SEGMENTO 4` and `SEGMENTO 5`, so that historical 4-digit records for Segments 1–3 never overwrite or duplicate 6-digit monthly data.
11. As an operador del sistema, I want the mart integrity gatekeeper to validate that Segmentos 4 and 5 are present, active, and excluded from `EC` monthly country aggregations before publishing to production, so that data corruption is caught before zero-downtime deployment.

## Implementation Decisions

- **Descubrimiento y extracción SEPS (Crawler & Extractor):**
  - Ampliar el descubridor de descargas del portal SEPS para reconocer la sección de **Estados Financieros Trimestrales (Bases de Datos)** además de las secciones mensuales y de patrimonio técnico, ignorando los boletines `.xlsm`.
  - Generalizar el extractor de archivos comprimidos para aceptar tanto `.txt` como `.csv` tabulados (cubriendo la serie 2018–2026) y normalizar variantes de encabezados (`SALDO (USD)` vs. `SALDO(USD)`, columnas adicionales como `DW CUENTAS.Desglose` en 2023, y fechas `YYYY-M-D` sin ceros a la izquierda).
  - Al procesar archivos trimestrales, filtrar estrictamente las filas correspondientes a `SEGMENTO 4` y `SEGMENTO 5` antes de almacenarlas en la capa intermedia trimestral.
- **Construcción de cubos analíticos y validación (ETL Marts & Gatekeeper):**
  - Actualizar la definición de `dim_segments` para asignar `reporting_frequency = 'quarterly'` a `SEGMENTO_4` y `SEGMENTO_5` (manteniendo `'monthly'` en `SEGMENTO_1`, `SEGMENTO_1_MUTUALISTA`, `SEGMENTO_2` y `SEGMENTO_3`).
  - Unificar en la construcción de hechos la lectura de la capa intermedia mensual (Segmentos 1–3) y la capa intermedia trimestral (Segmentos 4–5).
  - Calcular el **Agregado Nacional Mensual (`EC`)** únicamente sobre los segmentos con `reporting_frequency = 'monthly'` (ADR-0007).
  - Mantener en `NULL` los indicadores que dependen de subcuentas CUC de 6 dígitos (`liquidez_inmediata` Ficha 52, Fichas 19–27 de cobertura por cartera, Fichas 39–50 de rendimiento por cartera) cuando la entidad carezca de dichas subcuentas, así como las Fichas 58–63 de Patrimonio Técnico para Segmentos 4 y 5 (ADR-0007).
  - Calcular `dim_entities.is_active` comparando `last_period` de cada entidad contra el periodo máximo disponible de su propia frecuencia de reporte (`monthly` o `quarterly`).
  - Actualizar el validador de integridad (`ValidationReport`) para verificar las 6 definiciones de segmentos, la presencia de entidades activas en `SEGMENTO_4` y `SEGMENTO_5` y la consistencia del agregado `EC`.
- **Capa API y Contrato:**
  - Reutilizar el contrato OpenAPI existente (`Segment.reporting_frequency` con valores `monthly` | `quarterly`, y `SegmentCode` con `SEGMENTO_4` y `SEGMENTO_5`) sin cambios disruptivos de esquema.
  - Asegurar que el repositorio analítico y el cálculo de semáforo CAMEL manejen valores `NULL` en indicadores sin lanzar excepciones y emitiendo un estado neutral para indicadores no disponibles.
  - Asegurar que el cálculo de `entity_count` por segmento en metadatos refleje entidades activas según la frecuencia del segmento.
- **Interfaz de Usuario (Frontend):**
  - Mostrar un distintivo de periodicidad (`Trimestral`) en los selectores/filtros de segmento para `SEGMENTO_4` y `SEGMENTO_5` usando `reporting_frequency` proveniente de `/metadata/filters`.
  - Renderizar un badge neutral (`Sin dato`) en tarjetas, tablas y matriz CAMEL cuando un indicador venga en `null`, excluyéndolo del conteo de alertas regulatorias.

## Testing Decisions

- **Criterio de buenas pruebas:** Probar comportamiento observable en las costuras públicas (salidas Parquet validadas, respuestas JSON de endpoints FastAPI y renderizado de componentes React), sin acoplarse a detalles internos de implementación.
- **Costuras de prueba (seams) reutilizadas:**
  1. **Costura ETL / Marts (`etl:test` y pruebas de extractor):** Validar con fixtures tabulados (incluyendo variantes `.csv`, `SALDO(USD)`, fechas `YYYY-M-D` y filas mixtas de Segmentos 1–5) que el extractor filtra correctamente solo Segmentos 4 y 5, y validar sobre el mart construido que existen 6 segmentos con su `reporting_frequency` correcto, entidades activas en `SEGMENTO_4` y `SEGMENTO_5`, `NULL` en Ficha 52 / Fichas 58–63 para estos segmentos, y continuidad de `EC` sin incluir trimestrales.
  2. **Costura API Backend (`backend:test`):** Validar `/metadata/filters`, `/entities`, `/indicators/series` y `/supervision/camel` comprobando el retorno de `reporting_frequency: "quarterly"`, `is_active: true` para entidades de Segmentos 4 y 5 aunque el último periodo mensual sea posterior al último trimestre, y manejo seguro de indicadores en `null` en CAMEL.
  3. **Costura Frontend (`frontend:test`, `frontend:typecheck`, `frontend:build`):** Verificar en tests de componentes que los filtros muestran la etiqueta de periodicidad trimestral y que el comparador CAMEL renderiza un estado neutral (`Sin dato`) ante valores `null`.

## Out of Scope

- Parseo o ingesta de los boletines Excel con macros (`.xlsm`) de la sección *Reportes* de Estados Financieros Trimestrales.
- Aproximaciones contables a 4 dígitos para sustituir subcuentas de 6 dígitos (como usar `2103` completo en lugar de `210305`/`210310` en Liquidez Ficha 52).
- Creación de una serie agregada nacional trimestral separada que sume los 5 segmentos en `EC` (puede evaluarse en una iteración futura si se requiere).
- Cálculo o estimación sintética de Patrimonio Técnico / ACPR para Segmentos 2, 3, 4 o 5.

## Further Notes

- Referencias normativas y arquitectónicas: `GLOSSARY.md` y `docs/adr/0007-quarterly-segments-and-cuc-granularity.md`.
- Evidencia de fuentes primarias SEPS: `docs/research/seps-segmentos-4-5.md`.
