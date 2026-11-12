# Ticket 04: Guía de Puesta en Producción y Verificación Integral

Status: resolved
Blocked by: 01, 02, 03

## Descripción
1. Crear el manual operativo `docs/deployment/vercel-supabase.md`:
   - Pasos para crear el proyecto gratuito en Supabase y obtener la cadena de conexión `DATABASE_URL` (pooler puerto 6543 o directo 5432).
   - Pasos para importar el repositorio en Vercel, configurar las variables de entorno (`DATABASE_URL`, `SECRET_KEY`, `ENVIRONMENT=production`).
   - Verificación del primer acceso y cambio de clave del usuario `admin`.
   - Documentación de costos ($0) y límites de uso mensual.
2. Ejecutar la suite completa de pruebas locales:
   - `npm run contract:lint`
   - `npm run etl:test`
   - `npm run backend:test`
   - `npm run frontend:build`
   - `npm run test`
3. Confirmar todos los cambios con commits atómicos en Git.

## Criterios de Aceptación
1. Manual de despliegue claro, reproducible y probado.
2. 100% de las pruebas del sistema pasan con éxito.
3. El repositorio queda listo para conectar a Vercel con un solo clic.
