# ROADMAP ESTRATÉGICO DE DESPLIEGUE Y PRESENTACIÓN INSTITUCIONAL
**Proyecto de Investigación Científica ESPOCH – DI – 060**  
*"Plataforma Analítica e Interactiva del Sistema de Indicadores Financieros SFPS (SEPS Ecuador)"*  
**Titularidad:** Dirección de Investigación — Escuela Superior Politécnica de Chimborazo  
**Fecha:** Noviembre de 2026  
**Destinatarios:** Equipo de Investigación ESPOCH, Directivos del SFPS, Analistas de Riesgo y Auditoría

---

## 1. Visión General y Objetivos del Roadmap

El presente documento define la hoja de ruta integral para la puesta en producción, gobernanza operativa y transferencia de conocimiento de la plataforma analítica **ESPOCH – DI – 060**. Su propósito es garantizar un despliegue seguro, escalable y automatizado, acompañado de un protocolo de presentación ejecutiva de alto impacto ante autoridades universitarias, la Superintendencia de Economía Popular y Solidaria (SEPS) y directivos de cooperativas de ahorro y crédito y mutualistas del Ecuador.

```
                      CRONOGRAMA INTEGRAL DE DESPLIEGUE Y PRESENTACIÓN
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: DESPLIEGUE & INFRAESTRUCTURA (Semanas 1 y 2)                                   │
│  ├─ Dockerización multi-etapa (FastAPI + Vite/React + Reverse Proxy Caddy/Nginx)       │
│  ├─ Configuración de TLS/HTTPS institucional y secretos (.env.production)              │
│  └─ Backup y persistencia atómica de Data Marts en almacenamiento local/Cloud          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ FASE 2: AUTOMATIZACIÓN DEL PIPELINE DE DATOS (Semana 3)                                │
│  ├─ Cron job mensual de ingesta de nuevos boletines B11 y Patrimonio Técnico           │
│  ├─ Reconciliación atómica sin tiempo de inactividad (Zero-Downtime Parquet Switch)    │
│  └─ Alertas automatizadas de consistencia matemática (Spectral + Pytest)               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ FASE 3: PROTOCOLO DE PRESENTACIÓN EJECUTIVA (Semana 4)                                 │
│  ├─ Guión estructurado de Demo (Vista Pública vs. Vista Pro)                           │
│  ├─ Demostración del Semáforo CAMEL normativo y Benchmark multi-entidad                │
│  └─ Evidencia de rigor científico, velocidad analítica DuckDB y seguridad RBAC         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ FASE 4: TRANSFERENCIA Y GOBERNANZA INSTITUCIONAL (Semana 5+)                           │
│  ├─ Entrega de Manuales Técnicos y Metodológicos a la Dirección de Investigación      │
│  ├─ One-Pager Ejecutivo para gerencias de cooperativas                                 │
│  └─ Licenciamiento y convenio marco de cooperación interinstitucional                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Fase 1: Despliegue en Infraestructura y DevOps

### 2.1. Arquitectura de Despliegue en Contenedores (Docker Compose - Opción B)
Se implementa un esquema modular y orquestado con `docker-compose` para servidores propios institucionales (VPS Ubuntu Server 22.04 LTS o Rocky Linux / RHEL en la infraestructura ESPOCH):

```
                        TOPOLOGÍA DE CONTENEDORES (OPCIÓN B)
       Internet / Red Institucional ESPOCH
                        │ (Puerto 80 / 443)
                        ▼
       ┌─────────────────────────────────────────┐
       │ Contenedor Frontend & Reverse Proxy     │
       │ (sfps_frontend: Nginx Alpine)           │
       │ - Sirve bundles SPA (React 18 + Vite)   │
       │ - Compresión Gzip activada              │
       │ - Caché inmutable /assets/* (1 año)     │
       │ - Fallback SPA try_files a index.html   │
       └────────────────────┬────────────────────┘
                            │ (Proxy interno /api/*)
                            ▼
       ┌─────────────────────────────────────────┐
       │ Contenedor Backend API                  │
       │ (sfps_backend: Python 3.12-slim)        │
       │ - 4 Workers Uvicorn                     │
       │ - Motor DuckDB embebido en memoria      │
       │ - Validación OpenAPI 3.1 & RBAC JWT     │
       └────────────────────┬────────────────────┘
                            │ (Montura de Solo Lectura :ro)
                            ▼
       ┌─────────────────────────────────────────┐
       │ Volumen Persistente Data Marts          │
       │ ./data/processed/mart/ (21 MB Parquet)  │
       └─────────────────────────────────────────┘
```

#### Archivo `backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim AS backend
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt
COPY backend ./backend
COPY config ./config
COPY contracts ./contracts
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Archivo `frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY config/nginx-spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

#### Archivo `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: sfps_backend
    restart: unless-stopped
    env_file:
      - .env.production
    environment:
      - DATA_MART_DIR=/app/data/processed/mart
    volumes:
      - ./data/processed/mart:/app/data/processed/mart:ro
    networks:
      - sfps_network
    healthcheck:
      test: ["CMD-SHELL", "python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health")' || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    container_name: sfps_frontend
    restart: unless-stopped
    ports:
      - "${APP_PORT:-80}:80"
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - sfps_network

networks:
  sfps_network:
    driver: bridge
```

### 2.2. Configuración de Variables de Entorno Seguras (`.env.production`)
No almacenar credenciales por defecto en el repositorio. Crear el archivo `.env.production` a partir de la plantilla `.env.production.example` con permisos estrictos (`chmod 600 .env.production`):

```bash
# Servidor y Puerto Público
APP_PORT=80

# Seguridad Criptográfica JWT
# Generar clave segura: openssl rand -hex 32
JWT_SECRET_KEY="<CLAVE_CRIPTOGRAFICA_DE_32_BYTES_HEX>"
JWT_EXPIRE_HOURS=24

# Credenciales de Acceso Institucional (Vista Pro Acreditada)
ACCREDITED_USER="investigador.espoch"
ACCREDITED_PASSWORD="<PASSWORD_SEGURO_PRO>"
ADMIN_USER="admin.espoch"
ADMIN_PASSWORD="<PASSWORD_SEGURO_ADMIN>"

# Rutas internas de contenedores
DATA_MART_DIR="/app/data/processed/mart"
CORS_ORIGINS="http://localhost,http://localhost:80,http://127.0.0.1"
```

---
## 3. Fase 2: Estrategia de Mantenimiento y Automatización ETL

La SEPS publica la información financiera de las cooperativas con un desfase normativo de 30 a 45 días (cierre mensual).

### 3.1. Flujo de Actualización Automatizado (*Zero-Downtime Atomic Switch*)
Para evitar bloqueos o corrupción en DuckDB mientras los usuarios consultan la API:

1. **Ingesta en Carpeta Temporal:** El script mensual descarga y procesa los nuevos boletines en `data/processed/mart_incoming/`.
2. **Validación Automática de Integridad:** Se ejecuta `pytest etl/test_marts.py` sobre los datos nuevos. Si las 5 pruebas de consistencia matemática y cobertura pasan:
3. **Reemplazo Atómico:** Se actualiza el enlace simbólico (*symlink*) en Linux:
   ```bash
   ln -sfn /app/data/processed/mart_incoming /app/data/processed/mart_current
   ```
4. **Invalidación de Caché HTTP:** Se refresca la marca temporal `data_as_of` en los metadatos de la API, renovando automáticamente los ETags de todas las series.

---

## 4. Fase 3: Protocolo de Presentación Institucional (Demo Flow)

### 4.1. Estructura de la Sesión Ejecutiva (Tiempo Total: 45 minutos)

| Bloque | Tiempo | Objetivo | Contenido Clave a Exponer |
| :--- | :---: | :--- | :--- |
| **I. Apertura Institucional** | 5 min | Contextualizar el proyecto DI-060 | Relevancia del SFPS en la economía ecuatoriana ($> \$25\text{B}$ en activos), misión de la ESPOCH y transferencia científica. |
| **II. Rigor Normativo SEPS** | 10 min | Demostrar fidelidad regulatoria | Implementación de las **63 Fichas Metodológicas V3.0**, agregación nacional por **Ratio de Sumas** y cálculo de **Solvencia COMF Art. 190 (Ficha 62)**. |
| **III. Demo: Vista Pública** | 10 min | Transparencia y divulgación | 20 indicadores CAMEL, navegación histórica 2018–2025, filtros por segmento y provincia, gráficos interactivos con exportación de fichas. |
| **IV. Demo: Vista Acreditada Pro** | 15 min | Valor para Unidades de Riesgo | Inicio de sesión seguro (JWT), **Benchmarking multi-entidad simultáneo** (hasta 5 cooperativas vs. Segmento 1), semáforo CAMEL inteligente y descarga de microdatos. |
| **V. Conclusiones y Preguntas** | 5 min | Acuerdos y próximos pasos | Firma de actas de entrega, acceso a investigadores acreditados y apertura para convenios de cooperación. |

### 4.2. Guión Detallado para el Presentador (Storytelling Técnico-Financiero)

1. **El Problema del Sector:**  
   *"Históricamente, los analistas de riesgo de las cooperativas deben descargar archivos de Excel dispersos mes a mes para calcular ratios CAMEL de forma manual, exponiéndose a errores de fórmula y desactualización."*
2. **La Solución ESPOCH:**  
   *"La plataforma DI-060 procesa 22.7 millones de registros contables en 2 segundos mediante tecnología OLAP DuckDB, garantizando que el indicador que observa el directivo coincide exactamente con la metodología oficial de supervisión de la SEPS."*
3. **El Momento Clave (*Wow Factor*):**  
   - Seleccionar a **Jardín Azuayo**, **JEP** y **CREA** en el comparador de Benchmarking.
   - Mostrar la matriz consolidada generándose instantáneamente ($< 40\text{ ms}$).
   - Explicar el semáforo regulatorio: mostrar cómo la Ficha 62 valida el 17.5% de solvencia legal frente al 9% exigido por la ley ecuatoriana.

---

## 5. Fase 4: Entregables Formales y Transferencia

Para el cierre formal del proyecto de investigación ante la Dirección de Investigación de la ESPOCH, se deben radicar los siguientes documentos:

1. **Certificado de Auditoría y Homologación Técnica:**  
   Archivo [`docs/INFORME_AUDITORIA_FORENSE_ESPOCH_DI060.md`](file:///c:/Users/GlobalOffice/Desktop/Uprocach/SIstema_indicadores/docs/INFORME_AUDITORIA_FORENSE_ESPOCH_DI060.md), avalando el 100% de cumplimiento técnico y metodológico.
2. **Manual de Fichas Metodológicas del Sistema:**  
   Catálogo digital exportable desde la vista [`CatalogView`](file:///c:/Users/GlobalOffice/Desktop/Uprocach/SIstema_indicadores/frontend/src/components/views/CatalogView.tsx) con las 63 fichas SEPS, códigos contables B11 y umbrales normativos.
3. **Ficha Resumen Ejecutivo (One-Pager):**  
   Documento en formato PDF para los Consejos de Administración de las cooperativas participantes en la investigación.
4. **Repositorio Institucional:**  
   Código fuente versionado con contratos OpenAPI 3.1, suite de pruebas automatizadas y scripts de despliegue Docker listos para ejecución con un solo comando.