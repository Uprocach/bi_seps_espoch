# 01: Ingesta y extracción histórica de Bases Trimestrales SEPS (Segmentos 4 y 5)

**What to build:** El crawler y el extractor de datos SEPS descubren y descargan las Bases de Datos Trimestrales de Estados Financieros desde el portal oficial de la SEPS (serie histórica 2018–2026), normalizan sus variantes de formato y esquema (archivos `.txt` y `.csv` tabulados, encabezados `SALDO (USD)` vs. `SALDO(USD)`, columna adicional en 2023 y fechas `YYYY-M-D`), y persisten únicamente los registros de `SEGMENTO 4` y `SEGMENTO 5` en la capa intermedia trimestral, evitando duplicar o degradar los Segmentos 1–3 mensuales.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] El descubridor de descargas identifica los enlaces de la sección de Estados Financieros Trimestrales (Bases de Datos) por año, ignorando los boletines `.xlsm`.
- [x] El extractor procesa archivos comprimidos que contienen tanto `.txt` como `.csv` tabulados (serie 2018–2026) y normaliza las variantes de columnas y fechas sin errores de parseo.
- [x] Al procesar archivos trimestrales que incluyen segmentos 1–5 (2018–2025), se filtran estrictamente `SEGMENTO 4` y `SEGMENTO 5` antes de guardar en la capa intermedia trimestral.
- [x] Pruebas automatizadas con fixtures cubren todas las variantes de esquema (`.csv`, `SALDO(USD)`, columna extra 2023, fechas `YYYY-M-D`, filtrado exclusivo de Segmentos 4 y 5).
