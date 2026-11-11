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
- **Acceso Institucional Acreditado**: Acceso a microdatos detallados por cooperativa supervisada, diagnóstico y benchmarking CAMEL, bitácora de auditoría forense y gestión de credenciales.
  - `investigador`: Consulta analítica completa y exportación de microdatos en formato CSV.
  - `auditor`: Lo anterior más descarga de reportes ejecutivos en Excel y visualización de logs de auditoría forense.
  - `administrador`: Control total del sistema y gestión del padrón de usuarios acreditados.

## 5. Gestión de Identidades y Credenciales
- **Contraseña Temporal Inicial**: Credencial por defecto asignada automáticamente al crear o importar usuarios, equivalente al identificador de usuario institucional (`nombre.apellido`).
- **Cambio Obligatorio de Clave**: Regla de seguridad forzada mediante la bandera `must_change_password`, que bloquea la navegación interactiva hasta que el usuario establece una clave personal secreta de al menos 6 caracteres.
- **Restablecimiento Asistido de Contraseña**: Protocolo administrativo en el cual, ante el olvido de credenciales personales, el Administrador reinicia la cuenta a su contraseña temporal original con cambio obligatorio, registrando el evento en `audit_logs` (ADR-0002).
