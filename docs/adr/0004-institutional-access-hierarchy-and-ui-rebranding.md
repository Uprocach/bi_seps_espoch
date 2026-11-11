# 0004. Reestructuración de la Jerarquía de Acceso y Erradicación de Terminología Comercial ("Pro")

- **Fecha:** 2026-11-11
- **Estado:** Aceptado
- **Decisores:** Investigador Principal / Arquitectura de Software ESPOCH-DI-060

## Contexto

El sistema de indicadores financieros SFPS fue concebido bajo el proyecto de investigación científica **ESPOCH – DI – 060** con fines de supervisión macroprudencial y análisis regulatorio con la SEPS.
El uso de la nomenclatura *"Pro"* y *"Capa Pro"* en la interfaz visual, el menú de navegación lateral y los botones de autenticación transmitía equívocamente la idea de un servicio comercial de suscripción o de pago (*freemium/SaaS*), cuando en realidad la diferenciación responde únicamente a dos niveles de sensibilidad de la información:
1. Acceso Abierto: Estadísticas agregadas sectoriales públicas (país y segmentos SEPS).
2. Acceso Institucional Acreditado: Microdatos granulares por cooperativa supervisada, diagnósticos CAMEL, trazabilidad forense y gestión de padrón.

Asimismo, el menú lateral (Sidebar) presentaba una disposición continua sin segmentación funcional clara entre herramientas analíticas, fichas metodológicas y gobernanza.

## Decisión

1. **Erradicación de Términos Comerciales en la UI:**
   - Se eliminan todos los distintivos, badges dorados y textos referentes a *"Pro"*, *"Modo Pro"* o *"Capa Pro"*.
   - El botón de inicio de sesión público pasa a ser un sobrio **"Acceso Institucional"**.
   - Con sesión activa, se muestra el badge formal **"Acreditado"** junto con el rol correspondiente (*Investigador*, *Auditor*, *Administrador*).
   - En modo no autenticado, la UI no muestra etiquetas invasivas de *"Público"* ni advertencias de bloqueo comercial.
2. **Rebautizo del Módulo Comparativo:**
   - La vista *"Benchmarking Pro"* se renombra a **"Diagnóstico CAMEL & Benchmarking Institucional"**, enfatizando su rigor técnico y normativo.
3. **Jerarquización Modular del Sidebar:**
   - Se organiza el menú de navegación en 3 secciones temáticas con separadores visuales:
     - **ANÁLISIS FINANCIERO:** *Visión Global 360°*, *Dimensiones CAMEL*, *Diagnóstico CAMEL*, *Directorio COAC*.
     - **NORMATIVA Y REGULACIÓN:** *Catálogo SEPS v3.0*.
     - **GOBERNANZA INSTITUCIONAL:** *Bitácora de Auditoría* (Auditores/Admin), *Padrón de Usuarios* (Admin).
4. **Armonización de Glosario:**
   - Se actualiza [GLOSSARY.md](file:///C:/Users/GlobalOffice/Desktop/Uprocach/SIstema_indicadores/GLOSSARY.md) formalizando la distinción entre *Acceso Abierto (Macro/Sectorial)* y *Acceso Institucional Acreditado*.

## Consecuencias

- **Alineación Académica e Institucional:** La plataforma refleja fielmente su naturaleza de investigación pública y rigor regulatorio.
- **Claridad de Navegación:** El sidebar estructurado reduce la carga cognitiva y mejora la experiencia de usuario.
- **Sin Ruptura de Contratos:** Los endpoints técnicos internos mantienen compatibilidad retroactiva sin afectar el contrato OpenAPI ni los pipelines DuckDB.
