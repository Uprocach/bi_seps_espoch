# Ticket 01: Corrección de Superposición del Sidebar sobre el Contenido Global

**Status:** resolved  
**Tipo:** Bugfix / Layout  
**Blocked by:** Ninguno  

---

## Resolución
Se añadió la clase de desplazamiento dinámico responsive en `App.tsx`:
```tsx
<div
  className={`flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden transition-all duration-300 ease-in-out ${
    store.isSidebarCollapsed ? "lg:pl-20" : "lg:pl-72"
  }`}
>
```
Con esto, el área principal de contenido (TopBar, contenido central y footer) se desplaza exactamente los 288px (`lg:pl-72`) o los 80px (`lg:pl-20`) según el estado de colapso del menú lateral en desktop, mientras que en pantallas móviles permanece en `pl-0` sin solapamiento.  

---

## Descripción del Problema
El menú lateral (`Sidebar.tsx`) utiliza posicionamiento `fixed top-0 bottom-0 left-0 z-50` con anchos de `w-72` (288px) en estado expandido y `w-20` (80px) en estado colapsado.
En `App.tsx`, el contenedor principal de la aplicación (`<div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">`) no define un espaciado izquierdo en desktop. Como consecuencia, el sidebar se superpone directamente tapando los encabezados, tarjetas de resumen, gráficos y tablas en todas las vistas del sistema.

## Criterios de Aceptación
1. En pantallas de escritorio (`lg:`):
   - Cuando el sidebar está expandido (`!isSidebarCollapsed`), el área principal de contenido tiene un desplazamiento izquierdo de `lg:pl-72` (288px) o `lg:ml-72`.
   - Cuando el sidebar está colapsado (`isSidebarCollapsed`), el área principal de contenido tiene un desplazamiento izquierdo de `lg:pl-20` (80px) o `lg:ml-20`.
   - La transición entre expandido y colapsado es suave mediante `transition-all duration-300 ease-in-out`.
2. En pantallas móviles / tablets (`< lg`):
   - No se aplica desplazamiento izquierdo (`pl-0` / `ml-0`) ya que el sidebar es un drawer flotante con overlay backdrop.
3. El `TopBar` permanece alineado y visible sin ser tapado por el sidebar.
4. Las pruebas de compilación y visuales deben pasar sin regresiones.
