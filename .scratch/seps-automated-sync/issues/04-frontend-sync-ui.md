# Ticket 04: Interfaz de Control de Sincronización en Gobernanza

Status: ready-for-agent
Blocked by: 03

## Descripción
En la sección de Administración y Gobernanza Institucional, construir un panel de control interactivo:
- Tarjeta de conexión con `estadisticas.seps.gob.ec`.
- Comparativa visual: *Último corte en web SEPS* vs. *Último corte activo en el sistema*.
- Botón *"Sincronizar con Portal SEPS"* que dispara la tarea en segundo plano.
- Barra de progreso interactiva con polling no invasivo cada 2.5s mientras la tarea esté en ejecución.

## Criterios de Aceptación
1. Interfaz minimalista sin estilos pesados ni etiquetas comerciales ("Pro").
2. Notificación toast al iniciar y finalizar la sincronización.
3. Compilación limpia con Vite/TypeScript (`npm run frontend:build`).
