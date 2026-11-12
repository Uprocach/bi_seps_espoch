# Glosario de Dominio (SEPS / SFPS / ESPOCH-DI-060)

Términos y conceptos normativos oficiales utilizados en la plataforma analítica de indicadores financieros.

## 1. Entidades y Supervisión
- **SFPS**: Sector Financiero Popular y Solidario del Ecuador.
- **SEPS**: Superintendencia de Economía Popular y Solidaria (organismo de supervisión).
- **CUC**: Catálogo Único de Cuentas (nomenclatura contable unificada del sistema cooperativo).
- **Estructura B11**: Formato mensual obligatorio de balance financiero remitido a la SEPS.
- **COAC**: Cooperativa de Ahorro y Crédito.
- **Segmentos SEPS**:
  - `SEGMENTO_1`: Cooperativas con activos mayores a USD 80 millones.
  - `SEGMENTO_1_MUTUALISTA`: Asociaciones mutualistas de ahorro y crédito.
  - `SEGMENTO_2`: Cooperativas con activos entre USD 20M y 80M.
  - `SEGMENTO_3`, `SEGMENTO_4`, `SEGMENTO_5`: Cooperativas medianas y pequeñas.

## 2. Marco Analítico CAMEL
Metodología de supervisión y calificación de riesgo financiero:
- **C - Capital**: Solvencia patrimonial y suficiencia técnica (Fichas 1 y 62).
- **A - Calidad de Activos (Asset Quality)**: Morosidad de cartera y cobertura de provisiones (Fichas 5 y 18).
- **M - Manejo Administrativo (Management)**: Eficiencia operativa y gastos de personal (Ficha 31).
- **E - Rentabilidad (Earnings)**: Rendimiento sobre activos (ROA - Ficha 35) y sobre patrimonio (ROE - Ficha 34).
- **L - Liquidez (Liquidity)**: Fondos disponibles inmediatos sobre depósitos (Ficha 52).

## 3. Convenciones Matemáticas
- **Ratio de Sumas**: Todas las agregaciones a nivel segmento o país se computan como $\frac{\sum \text{numeradores}}{\sum \text{denominadores}}$, nunca como promedio de ratios individuales.
- **Polaridad**:
  - `higher_is_better`: Mientras más alto sea el valor, mejor es la salud financiera (ej. ROA, Liquidez, Cobertura).
  - `lower_is_better`: Mientras menor sea el valor, mejor es la salud financiera (ej. Morosidad, Gastos Operativos).
  - `neutral`: Un valor intermedio o en rango óptimo es el deseable (ej. Intermediación Financiera).

## 4. Niveles de Acceso y Roles (RBAC)
- **Acceso Abierto (Macro/Sectorial)**: Indicadores agregados del sector cooperativo a nivel país y segmento SEPS, y catálogo normativo de fichas metodológicas.
- **Acceso Institucional Acreditado (Supervisión)**: Dominio formal que sustituye de manera definitiva la terminología histórica "Pro". Otorga acceso a microdatos detallados por cooperativa supervisada, diagnóstico y benchmarking CAMEL, bitácora de auditoría forense y gestión de credenciales.
  - `investigador`: Consulta analítica completa y exportación de microdatos en formato CSV.
  - `auditor`: Lo anterior más descarga de reportes ejecutivos en Excel y visualización de logs de auditoría forense.
  - `administrador`: Control total del sistema y gestión del padrón de usuarios acreditados.

## 5. Gestión de Identidades y Credenciales
- **Contraseña Temporal Inicial**: Credencial por defecto asignada automáticamente al crear o importar usuarios, equivalente al identificador de usuario institucional (`nombre.apellido`).
- **Cambio Obligatorio de Clave**: Regla de seguridad forzada mediante la bandera `must_change_password`, que bloquea la navegación interactiva hasta que el usuario establece una clave personal secreta de al menos 6 caracteres.
- **Restablecimiento Asistido de Contraseña**: Protocolo administrativo en el cual, ante el olvido de credenciales personales, el Administrador reinicia la cuenta a su contraseña temporal original con cambio obligatorio, registrando el evento en `audit_logs` (ADR-0002).

## 6. Pipeline de Datos y Despliegue Atómico (Fase 2)
- **Data Mart Staging (`mart_staging`)**: Directorio de preparación aislado donde el motor ETL consolida los nuevos cubos multidimensionales Parquet antes de su validación y paso a producción.
- **Gatekeeper Validador Estructurado (`ValidationReport`)**: Función pura de verificación matemática e integridad referencial de Parquet en staging, que audita el 100% de los datos antes del reemplazo atómico sin mutar variables de entorno ni invocar arneses de testing en procesos web concurrentes.
- **Reemplazo Atómico Zero-Downtime (*Zero-Downtime Atomic Switch*)**: Protocolo por el cual la API conmuta de inmediato hacia el nuevo Data Mart sin reiniciar el servidor ni interrumpir lecturas concurrentes activas de DuckDB, invalidando automáticamente los encabezados de caché HTTP ETag.
- **Puntero Activo de Datos (`CURRENT_MART`)**: Archivo de metadatos o enlace simbólico que determina en caliente cuál partición física de datos está activa para las consultas analíticas del sistema.

## 7. Módulos y Costuras Arquitectónicas
- **Motor Analítico Consolidado (`AnalyticsRepository`)**: Módulo profundo que concentra la conexión multihilo a DuckDB, la resolución de metadatos y la ejecución de consultas optimizadas sobre cubos Parquet Hive (series, entidades, benchmarking CAMEL y microdatos en bruto).
- **Formateador de Exportación (`ExportFormatter`)**: Adaptador especializado de serialización que convierte conjuntos de datos estructurados en streaming CSV con BOM UTF-8 o libros de trabajo Excel con formato estilizado, completamente desacoplado de la capa de acceso a datos.
- **Cliente HTTP Profundo**: Módulo de red en frontend que encapsula las peticiones a la API institucional, asume la sesión mediante cookies HttpOnly y traduce los errores a contratos de problema RFC 9457 sin dispersar tokens en memoria.
