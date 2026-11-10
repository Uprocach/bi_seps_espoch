# Sistema de Indicadores Financieros SFPS (SEPS Ecuador)
### Arquitectura Spec-Driven Development (SDD)

Plataforma analítica integral de indicadores financieros para el sector cooperativo de Ecuador (SEPS), construida bajo metodología **Spec-Driven Development** a partir de los balances mensuales de la estructura **B11** (2018–2025) y las **Fichas Metodológicas Oficiales V3.0**.

---

## 🏗️ Stack Tecnológico

- **Contrato Vinculante (SDD):** OpenAPI 3.1.0 ([`contracts/openapi.yaml`](contracts/openapi.yaml)) con linter estricto Spectral ([`contracts/.spectral.yaml`](contracts/.spectral.yaml)) y servidor mock Prism.
- **Motor ETL:** Python + DuckDB (vectorizado, procesa 22.7M registros en 2.0s) procesando hacia [`data/processed/mart/`](data/processed/mart/).
- **Base de Datos de Producción:** Supabase / PostgreSQL con DDL optimizado ([`contracts/supabase_schema.sql`](contracts/supabase_schema.sql)).
- **Backend:** FastAPI (Python) validado contra el contrato OpenAPI con respuestas de error RFC 9457 (`application/problem+json`).
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS + **shadcn/ui** con paleta financiera (esmeralda, bosque, oro/ámbar y tonos pastel para gráficos Recharts).
- **Tipado End-to-End:** Tipos de TypeScript autogenerados directamente desde el contrato OpenAPI ([`frontend/src/types/api.ts`](frontend/src/types/api.ts)).

---

## 📊 Indicadores Implementados

| Indicador | Ficha SEPS | Fórmulas Contables CUC | Sentido Deseable |
| :--- | :--- | :--- | :--- |
| **Morosidad de Cartera Total** | Ficha 5 | `cartera_improductiva / (c14 - c1499) * 100` | Menor es mejor |
| **Cobertura de Cartera Improductiva** | Ficha 18 | `(-c1499) / cartera_improductiva * 100` | Mayor es mejor |
| **ROA (Rentabilidad sobre Activos)** | Ficha 35 | Ene-Nov: `((c5 - c4) * 12 / mes) / activo_promedio_ytd * 100`<br>Dic: `(c3603 + c3604) / c1 * 100` | Mayor es mejor |
| **ROE (Rentabilidad sobre Patrimonio)** | Ficha 34 | Ene-Nov: `((c5 - c4) * 12 / mes) / patrimonio_promedio_ytd * 100`<br>Dic: `resultado_cierre / (c3 - resultado_cierre) * 100` | Mayor es mejor |
| **Solvencia Patrimonial (Suficiencia)** | Ficha 1 | `(c3 + anualizado(c5 - c4)) / act_inmo_net * 100` | Mayor es mejor |
| **Liquidez Inmediata** | Ficha 52 | `c11 (Fondos Disponibles) / c21 (Depósitos) * 100` | Mayor es mejor |
| **Intermediación Financiera** | Ficha 36 | `cartera_bruta / c21 (Depósitos) * 100` | Neutral |
| **Eficiencia Operativa** | Ficha 31 | `(c45 (Gastos Operación) * 12 / mes) / activo_promedio_ytd * 100` | Menor es mejor |

*Nota Técnica:* Todas las agregaciones a nivel segmento y país se calculan mediante **ratio de sumas** ($\frac{\sum \text{numeradores}}{\sum \text{denominadores}}$), replicando fielmente la metodología de agregación del sistema cooperativo ecuatoriano.

---

## 🚀 Comandos de Ejecución

Desde la raíz del proyecto:

### 1. Pruebas y Validación Integral (Full-Stack)
```bash
npm run test
```
Ejecuta secuencialmente:
1. `npm run contract:lint`: Validación estricta Spectral del contrato OpenAPI.
2. `npm run etl:test`: Pruebas de consistencia matemática y conciliación de Data Marts.
3. `npm run backend:test`: Pruebas de integración del backend FastAPI contra el contrato.
4. `npm run frontend:build`: Compilación TypeScript y empaquetado de producción con Vite.

### 2. Pipeline de Datos (DuckDB ETL)
```bash
# Ejecutar pipeline y regenerar los Data Marts en data/processed/mart/
npm run etl:run

# Validar integridad matemática de los Data Marts
npm run etl:test
```

### 3. Backend (FastAPI)
```bash
# Iniciar servidor de desarrollo en http://localhost:8000
npm run backend:dev

# Ejecutar tests del backend
npm run backend:test
```

### 4. Frontend (React + Vite + Tailwind + shadcn/ui)
```bash
# Iniciar frontend de desarrollo en http://localhost:5173
npm run frontend:dev

# Regenerar tipos TypeScript desde el contrato OpenAPI
npm run frontend:codegen

# Compilar para producción
npm run frontend:build
```

### 5. Mock Server (Prism)
```bash
# Levantar servidor mock en el puerto 4010 con validación de contrato
npm run contract:mock
```
