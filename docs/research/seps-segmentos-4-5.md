# Investigación: Publicación de Estados Financieros e Indicadores SEPS para Segmentos 4 y 5

Fecha de investigación: 2026-11-18  
Fuentes primarias consultadas:
- Portal oficial de estadísticas SFPS de la SEPS: `https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/`
- Descarga directa SEPS `download_id=3443` (`2026_EEFF_Trim.txt`): `https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=3443`
- Archivos raw locales descargados previamente desde SEPS en `data/raw/Situación Financiera/`
- Código fuente del repositorio: `etl/seps_crawler.py`, `etl/build_marts.py`, `etl/ingest_patrimonio_tecnico.py`, `config/indicators_spec.json`, `contracts/openapi.yaml`, `backend/app/services/repository.py`, `GLOSSARY.md`

---

## 1. Cómo publica la SEPS los datos de los Segmentos 4 y 5

### 1.1 Ubicación en el portal oficial de la SEPS
En `https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/`, dentro de la sección **Situación Financiera**, la SEPS separa la publicación según frecuencia y cobertura de segmentos:

1. **Estados Financieros Mensuales** (Reportes y Bases de Datos):
   - Texto del portal: *"Cooperativas de ahorro y crédito de los segmentos 1, 2, 3, asociaciones mutualistas de ahorro y crédito para la vivienda, Caja Central FINANCOOP y CONAFIPS."*
   - Las Bases de Datos se publican a **6 dígitos** del Catálogo Único de Cuentas (CUC).
   - **No incluye** a las cooperativas de Segmento 4 ni Segmento 5.

2. **Estados Financieros Trimestrales** (Reportes y Bases de Datos):
   - **Reportes** (`descarga_2956.zip` para 2025, `download_id=3434` para 2026): *"Reportes que contienen los estados financieros, estado de pérdidas y ganancias y principales indicadores financieros de las cooperativas de ahorro y crédito de los segmentos 4 y 5."* Contienen libros Excel `.xlsm` (p. ej. `Boletín Financiero Segmento 4_Sep2025.xlsm`, `Boletín Financiero Segmento 5_Sep2025.xlsm`) con hojas de estado financiero, resultados, clasificación de cartera y ranking.
   - **Bases de Datos** (`download_id=3443` para 2026; `2961` para 2025; `2489` para 2024; `2105` para 2023; `1314` para 2022; `901` para 2021; `902` para 2020; `903` para 2019; `904` para 2018): *"Estados Financieros a 4 dígitos de las cooperativas de ahorro y crédito de los segmentos 1, 2, 3, 4, 5 y asociaciones mutualistas de ahorro y crédito para la vivienda."*

3. **Patrimonio técnico** (Reportes):
   - Texto del portal: *"Reportes que contienen el patrimonio técnico y la solvencia de las cooperativas de ahorro y crédito del segmento 1, asociaciones mutualistas de ahorro y crédito para la vivienda y Caja Central FINANCOOP."*
   - La SEPS **no publica** reportes de Patrimonio Técnico / ACPR para los Segmentos 4 y 5 (tampoco para los Segmentos 2 y 3).

### 1.2 Frecuencia de reporte y último corte disponible
- **Frecuencia**: **Trimestral** (cortes al 31 de marzo, 30 de junio, 30 de septiembre y 31 de diciembre).
- **Último corte verificado en línea** (`https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=3443`, archivo `2026_EEFF_Trim.txt`):
  - **Última fecha de corte**: **`2026-09-30`** (`"2026-9-30"`).
  - Cortes presentes en 2026: `2026-3-31`, `2026-6-30`, `2026-9-30`.
  - Cobertura en `2026_EEFF_Trim.txt`: únicamente `SEGMENTO 4` (**135 entidades**) y `SEGMENTO 5` (**49 entidades**). En cambio, el archivo `2025_EEFF_Trim.txt` (`descarga_2961.zip`) incluía los 5 segmentos a 4 dígitos (`SEGMENTO 1`: 44, `SEGMENTO 1 MUTUALISTA`: 4, `SEGMENTO 2`: 65, `SEGMENTO 3`: 100, `SEGMENTO 4`: 144, `SEGMENTO 5`: 53).

### 1.3 Formato de archivo, esquema y granularidad contable (CUC)
Inspección directa de los archivos en `data/raw/Situación Financiera/Bases de Datos/Estados Financieros Trimestrales/` y de `2026_EEFF_Trim.txt` (`download_id=3443`):

| Archivo / Año | Formato dentro del ZIP | Columnas / Particularidades |
|---|---|---|
| `2026_EEFF_Trim.txt` (`3443`) | `.txt` tabulado, comillas `"` | 7 columnas: `FECHA DE CORTE`, `SEGMENTO`, `RUC`, `RAZON SOCIAL`, `CUENTA`, `DESCRIPCION CUENTA`, `SALDO (USD)` |
| `2025_EEFF_Trim.txt` (`2961`), `2024_EEFF_Trim.txt` (`2489`) | `.txt` tabulado, comillas `"` | 7 columnas idénticas a 2026 |
| `2023_EEFF-Trim.txt` (`2105`) | `.txt` tabulado sin comillas | **8 columnas**: agrega `DW CUENTAS.Desglose` al final |
| `2022b.txt` (`1314`), `2021.txt` (`901`) | `.txt` tabulado | 7 columnas, pero la columna de monto es **`SALDO(USD)`** (sin espacio) |
| `2020.csv` (`902`), `2019.csv` (`903`), `2018.csv` (`904`) | **`.csv`** (tabulado a pesar de la extensión) | Extensión `.csv` en lugar de `.txt`; columna **`SALDO(USD)`** (sin espacio) |

- **Formato de fecha**: `YYYY-M-D` sin ceros a la izquierda en mes/día (p. ej. `2026-9-30`, `2022-6-30`).
- **Granularidad CUC**: Máximo **4 dígitos** (longitudes de `CUENTA` verificadas en `2025_EEFF_Trim.txt`: `1`, `2` y `4` dígitos), a diferencia de `Estados Financieros Mensuales` que reporta a **6 dígitos**.

---

## 2. Brechas y compatibilidad con el código actual

Actualmente `data/processed/mart/fct_indicators_entity_monthly.parquet` **no contiene ningún registro** de `SEGMENTO_4` ni `SEGMENTO_5` (solo `SEGMENTO_1` con 49 entidades, `SEGMENTO_1_MUTUALISTA` con 4, `SEGMENTO_2` con 90 y `SEGMENTO_3` con 162, hasta `2026-09`).

### 2.1 Crawler e ingesta (`etl/seps_crawler.py`)
1. **Sección ignorada en `discover_downloads()`** (`etl/seps_crawler.py:60-95`): Solo clasifica enlaces bajo `"patrimonio"` y `"estados financieros mensuales"`. Los enlaces de `"estados financieros trimestrales"` quedan descartados.
2. **Filtro estricto de extensión `.txt`** (`etl/seps_crawler.py:159`): `if name.lower().endswith(".txt"):` ignora los archivos `2018.csv`, `2019.csv` y `2020.csv` de las bases trimestrales históricas.
3. **Nombre de columna rígido `"SALDO (USD)"`** (`etl/seps_crawler.py:185`): Falla al procesar `2022b.txt`, `2021.txt` y `2020.csv`, donde el encabezado es `"SALDO(USD)"` (sin espacio).

### 2.2 Dimensión de segmentos y contrato OpenAPI (`etl/build_marts.py`, `contracts/openapi.yaml`)
- **Contrato preparado**: `contracts/openapi.yaml:961-971` (`SegmentCode`) ya enumera `SEGMENTO_4` y `SEGMENTO_5`; `contracts/openapi.yaml:1050-1054` (`Frequency`) define `enum: [monthly, quarterly]`; y `Segment.reporting_frequency` (`contracts/openapi.yaml:1057-1070`) expone la frecuencia por segmento.
- **ETL desalineado**: `etl/build_marts.py:45-52` (`SEGMENTS_DEF`) declara `reporting_frequency: "monthly"` para `SEGMENTO_4` y `SEGMENTO_5`, y `etl/build_marts.py:14,75` (`INTERIM_DIR`) solo lee `data/interim/situacion_financiera/estados_financieros_mensuales/*.parquet`.
- **Glosario**: `GLOSSARY.md:11-15` menciona `SEGMENTO_4` y `SEGMENTO_5` sin distinguir su frecuencia trimestral ni sus umbrales de activos.

### 2.3 Fórmulas CUC a 6 dígitos vs. base trimestral a 4 dígitos (`etl/build_marts.py`, `config/indicators_spec.json`)
La mayoría de los indicadores principales (activos `1`, fondos disponibles `11`, cartera `14`/`1499`, cartera improductiva según `config/indicators_spec.json:21-78` que usa códigos de 4 dígitos `1425`–`1489`, depósitos `21`, patrimonio `3`, gastos `4`, ingresos `5`) utilizan cuentas de 1 a 4 dígitos y **sí** pueden calcularse con la base trimestral.

Sin embargo, existen **tres grupos de cuentas de 6 dígitos** en `etl/build_marts.py` que **no existen** en las bases trimestrales a 4 dígitos:
1. **Ficha 52 (`liquidez_inmediata`)** — `etl/build_marts.py:103,595-599`: `depo_corto_plazo` filtra `cuenta IN ('2101', '2102', '210305', '210310')`. Al faltar `210305` y `210310` en la base trimestral, el denominador subestima los depósitos a corto plazo (o distorsiona la liquidez al alza).
2. **Fichas 19–27 (Cobertura de provisiones por tipo de cartera)** — `etl/build_marts.py:149-157`: depende de cuentas `149905`–`149955` (6 dígitos), ausentes en la base trimestral.
3. **Fichas 39–50 (Rendimiento por tipo de cartera)** — `etl/build_marts.py:159-169`: depende de cuentas `510405`–`510435` (6 dígitos), ausentes en la base trimestral.

### 2.4 Patrimonio Técnico / ACPR (`etl/ingest_patrimonio_tecnico.py`, `etl/build_marts.py`)
- Las Fichas 58–63 (`etl/build_marts.py:634-668`) provienen exclusivamente de `etl/ingest_patrimonio_tecnico.py`, cuyos boletines SEPS solo cubren Segmento 1, Mutualistas y FINANCOOP. Para Segmentos 4 y 5 estos 6 indicadores permanecerán sin datos (`NULL` / ausentes).
- Nota de seguridad en `etl/ingest_patrimonio_tecnico.py:126`: si un RUC no está en `dim_entities`, asigna por defecto `"SEGMENTO_1"` (riesgo de clasificación errónea si llegara un RUC fuera de catálogo).

### 2.5 Impacto en agregaciones, YTD y estado activo (`etl/build_marts.py`, `backend/app/services/repository.py`)
1. **Distorsión en `fct_indicators_country_monthly`** (`etl/build_marts.py:698-721`): Esta tabla agrupa `fct_indicators_entity_monthly` directamente por `(period, indicator_id)`. Si se ingieren `SEGMENTO_4` y `SEGMENTO_5` únicamente en los meses de cierre trimestral (`03`, `06`, `09`, `12`), la serie nacional sufrirá saltos artificiales (efecto sierra) cada 3 meses al sumar ~184 entidades adicionales en esos meses y excluirlas en los meses intermedios (`01, 02, 04, 05, 07, 08, 10, 11`).
2. **Promedios YTD** (`etl/build_marts.py:252-270`): `AVG(...) OVER (PARTITION BY ruc, anio ...)` promediará entre 1 y 4 observaciones trimestrales para Segmentos 4 y 5 frente a 1–12 observaciones mensuales para Segmentos 1–3. La anualización `* 12.0 / mes` (`etl/build_marts.py:239-240,481,492`) sí es algebraicamente consistente para `mes IN (3, 6, 9, 12)`.
3. **Falso inactivo en `dim_entities.is_active`** (`etl/build_marts.py:189,219` y `backend/app/services/repository.py:67-68`): `is_active` se calcula como `(a.last_period = '{latest_period}')` usando el `MAX(period)` global. Cuando los datos mensuales de Segmentos 1–3 avancen 1 o 2 meses por delante del último cierre trimestral de Segmentos 4–5 (p. ej. `2026-10` vs `2026-09`), todas las entidades de Segmentos 4 y 5 quedarían marcadas con `is_active = FALSE` y su `entity_count` en `/metadata/filters` caería a `0`.
