# Ticket 02: Motor de Rastreo y Descarga SEPS (Crawler)

Status: ready-for-agent
Blocked by: 01

## Descripción
Implementar `etl/seps_crawler.py` para consultar el portal `https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/`, detectar enlaces de descarga mediante el patrón `?sdm_process_download=1&download_id=...`, descargar el archivo ZIP de balances B11 en memoria o temporal, y transformar los datos a la estructura canónica Parquet de 7 columnas en `data/interim/situacion_financiera/estados_financieros_mensuales/`.

## Criterios de Aceptación
1. Soporta inspección en vivo de la página web de la SEPS.
2. Detección automática del periodo contable.
3. Validación de integridad de estructura antes de escribir el Parquet interim.
