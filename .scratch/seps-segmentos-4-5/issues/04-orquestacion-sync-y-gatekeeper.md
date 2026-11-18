# 04: Orquestación automática de sincronización trimestral y Gatekeeper de integridad

**What to build:** El pipeline automatizado de sincronización periódica con la SEPS descarga y procesa tanto bases mensuales como trimestrales en cada ejecución, y el Gatekeeper validador (`ValidationReport`) audita la presencia de los 6 segmentos, la existencia de entidades activas en `SEGMENTO_4` y `SEGMENTO_5` y la continuidad del Agregado Nacional Mensual (`EC`) antes de ejecutar el reemplazo atómico sin tiempo de inactividad. La suite integral de verificación del proyecto pasa en verde.

**Blocked by:** 01: Ingesta y extracción histórica de Bases Trimestrales SEPS (Segmentos 4 y 5), 02: Cubos analíticos, API y Dashboard Macro para Segmentos 4 y 5 (Trimestral, EC y nulidad CUC)

**Status:** ready-for-agent

- [ ] El orquestador de sincronización automática detecta y procesa nuevos cortes tanto de Estados Financieros Mensuales como de Estados Financieros Trimestrales.
- [ ] El Gatekeeper validador (`ValidationReport`) verifica la integridad matemática y referencial de los 6 segmentos (incluyendo entidades activas en Segmento 4 y 5 y exclusión de trimestrales en `EC`) antes de conmutar el mart activo.
- [ ] Toda la suite de verificación integral del repositorio (`contract:lint`, `guardrails:check`, `etl:test`, `backend:test`, `frontend:typecheck`, `frontend:test`, `frontend:build`) pasa sin errores.
