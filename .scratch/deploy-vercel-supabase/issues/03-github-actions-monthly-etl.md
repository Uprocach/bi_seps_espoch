# Ticket 03: Orquestación del ETL Mensual con GitHub Actions

Status: resolved
Blocked by: none

## Descripción
1. Crear el workflow `.github/workflows/monthly-etl.yml`:
   - Triggers:
     - Cron programado: `0 3 18,25 * *` (días 18 y 25 a las 03:00 UTC).
     - Disparador manual: `workflow_dispatch` con parámetro opcional `force: boolean`.
   - Pasos del Job:
     1. `actions/checkout@v4` con token para permitir push de datos actualizados.
     2. `actions/setup-python@v5` con Python 3.12 y cache de pip.
     3. Instalación de dependencias: `pip install -r requirements.txt`.
     4. Ejecución del pipeline: `python etl/monthly_pipeline.py`.
     5. Verificación estricta de integridad de los marts generados: `python etl/test_marts.py`.
     6. Si se detectan cambios en `data/processed/mart/` y las 7 pruebas matemáticas pasan:
        - Configurar git bot.
        - Hacer commit atómico: `chore(data): automated monthly SEPS update [skip ci]`.
        - Push a la rama principal `master`.

## Criterios de Aceptación
1. El archivo YAML de GitHub Actions es sintácticamente válido.
2. Si la SEPS no tiene nuevos archivos, el job finaliza de forma limpia sin errores ni commits vacíos.
3. El workflow no permite push si alguna prueba de `etl/test_marts.py` falla.
