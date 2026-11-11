# 0005. Pipeline Automatizado de Datos con Reemplazo Atómico Zero-Downtime

- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Decisores:** Investigador Principal / Equipo de Datos ESPOCH-DI-060

## Contexto

La Superintendencia de Economía Popular y Solidaria (SEPS) publica mensualmente nuevos boletines financieros (estructura contable B11) y reportes de Patrimonio Técnico (ACPR).
La plataforma analítica ESPOCH-DI-060 procesa estos datos en memoria mediante DuckDB directamente sobre archivos Parquet particionados ubicados en `data/processed/mart/`.

En un entorno de producción, la ingesta de un nuevo periodo contable no puede:
1. Requerir reiniciar el servidor web FastAPI ni detener los contenedores en ejecución.
2. Interrumpir o bloquear consultas analíticas concurrentes activas de los usuarios en línea.
3. Exponer datos corruptos, incompletos o con fallas metodológicas si un boletín contiene errores de origen.
4. Mantener en caché respuestas obsoletas una vez que el nuevo periodo ha sido incorporado.

## Decisión

Se implementa una arquitectura de pipeline automatizado con **Reemplazo Atómico Zero-Downtime (*Zero-Downtime Atomic Switch*)** compuesta por cuatro etapas:

1. **Aislamiento en Staging (`mart_staging`):**
   - El script orquestador `etl/monthly_pipeline.py` construye los cubos Parquet en una carpeta aislada de preparación (`data/processed/mart_staging/`), sin tocar el Data Mart activo de producción.

2. **Gatekeeper Automatizado de Calidad (Integridad 100%):**
   - Antes de cualquier conmutación, se ejecuta la suite de validación `etl/test_marts.py` contra `mart_staging`.
   - Se verifican 5 reglas críticas: 24 provincias, 6 segmentos, $\ge 200$ entidades con RUC válido de 13 dígitos terminado en 001, y consistencia matemática exacta ($\text{ratio} = \frac{\text{numerador}}{\text{denominador}} \times 100$).
   - Si una sola prueba falla, el proceso aborta, se envía una alerta y el sistema productivo continúa operando con el Data Mart previo sin alteración alguna.

3. **Reemplazo Atómico Multi-Plataforma:**
   - En Linux/Docker: Mediante enlace simbólico atómico `ln -sfn mart_staging mart_current`.
   - En Windows/Híbrido: Mediante archivo puntero de metadatos atómico `data/processed/CURRENT_MART` y swap seguro con `os.replace`.
   - `MartPathProvider` (`backend/app/services/mart_provider.py`) lee dinámicamente el puntero activo, garantizando que nuevas consultas DuckDB apunten de inmediato a la nueva partición sin bloquear lecturas en curso.

4. **Invalidación de Caché HTTP ETag y Auditoría:**
   - La fecha de corte `data_as_of` y el periodo máximo se actualizan automáticamente en `/api/v1/indicators/metadata`.
   - Como las semillas de los ETags (`ETag: W/"..."`) incluyen el periodo y la versión de datos, todos los navegadores y proxies invalidan su caché de inmediato.
   - El evento de actualización y switch queda registrado inmutablemente en la bitácora `audit_logs` de SQLite WAL con el detalle del periodo incorporado y el total de registros procesados.

5. **Exposición en Contrato OpenAPI 3.1.0:**
   - Se formaliza el endpoint administrativo `GET /api/v1/admin/pipeline-status` para que los auditores y administradores monitoreen el estado del Data Mart, la fecha de último switch y la disponibilidad de datos en staging.

## Consecuencias

- **Alta Disponibilidad:** Actualizaciones mensuales transparentes con cero segundos de inactividad.
- **Tolerancia a Fallos:** Imposibilidad de que datos con errores de cuadre contable pasen a la vista pública o de análisis.
- **Trazabilidad:** Registro forense completo de cada ciclo de ingesta en la base de datos institucional.
- **Cumplimiento SDD:** Contrato OpenAPI auditado con Spectral antes de la implementación técnica.
