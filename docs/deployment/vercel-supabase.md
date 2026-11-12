# Guía Operativa de Despliegue Zero-Cost: Vercel + Supabase + GitHub Actions (ADR-0006)

Plataforma de Indicadores Financieros SFPS (ESPOCH-DI-060).
Esta guía detalla los pasos para poner en marcha el sistema en producción con costo perpetuo cero ($0 USD), manteniendo el contrato OpenAPI 3.1.0, el motor analítico DuckDB y la gobernanza de identidades intactos.

---

## 1. Configuración de Base de Datos en Supabase (Free Tier)

1. Ingresa a [supabase.com](https://supabase.com/) e inicia sesión (con tu cuenta de GitHub).
2. Haz clic en **New project**.
   - **Name:** `espoch-sfps-db` (o el nombre de tu preferencia).
   - **Database Password:** Elige una contraseña segura y anótala.
   - **Region:** Selecciona `East US (North Virginia)` o `South America (São Paulo)`.
   - **Pricing Plan:** Free ($0/mes).
3. Una vez creado el proyecto, dirígete a:
   **Project Settings** (icono de engranaje) -> **Database**.
4. En la sección **Connection string**, selecciona la pestaña **URI**:
   - Copia la cadena en modo **Transaction Pooler** (puerto `6543`) o **Direct** (puerto `5432`):
     ```
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
   - Reemplaza `[YOUR-PASSWORD]` con la contraseña real que creaste en el paso 2.

> [!NOTE]
> No es necesario ejecutar ningún script SQL manual en el SQL Editor de Supabase. El backend FastAPI crea de manera automática e idempotente las tablas `users` y `audit_logs` y siembra el usuario administrador institucional en su primer arranque.

---

## 2. Despliegue en Vercel

1. Ingresa a [vercel.com](https://vercel.com/) e inicia sesión con GitHub.
2. Haz clic en **Add New...** -> **Project**.
3. Importa el repositorio del proyecto `SIstema_indicadores`.
4. En la pantalla de configuración del proyecto:
   - **Framework Preset:** Selecciona `Vite` (o déjalo en `Other`, Vercel lo detectará automáticamente gracias a `vercel.json`).
   - **Root Directory:** Déjalo en `./` (la raíz del repositorio).
5. Despliega la sección **Environment Variables** y agrega las siguientes 3 variables:

| Nombre de Variable | Valor | Descripción |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres.[REF]:[PASS]@...:6543/postgres` | Cadena URI de Supabase copiada en el paso 1. |
| `SECRET_KEY` | *(Genera un string aleatorio de 32+ caracteres)* | Llave criptográfica para firmas JWT y cookies HttpOnly. |
| `ENVIRONMENT` | `production` | Activa modo seguro (cookies con flag `Secure` y `SameSite=Lax`). |

6. Haz clic en **Deploy**.
7. En ~1 minuto, Vercel compilará la SPA React en Vite y desplegará la función serverless Python en `/api/index.py`.

---

## 3. Primer Acceso y Cambio Obligatorio de Clave

1. Abre la URL asignada por Vercel (ej. `https://espoch-sfps.vercel.app`).
2. Haz clic en **Acceso Acreditado** o **Iniciar Sesión**.
3. Ingresa las credenciales maestras iniciales:
   - **Usuario:** `admin.espoch`
   - **Contraseña:** `EspochAdmin2026#`
4. El sistema detectará automáticamente la bandera de primer acceso (`must_change_password`) y presentará el modal obligatorio de actualización de credenciales.
5. Define tu contraseña definitiva (mínimo 6 caracteres). A partir de ese momento, el usuario queda activado con rol de `administrador`.

---

## 4. Configuración de GitHub Actions para el ETL Mensual Automático

Para que el workflow mensual programado pueda confirmar y actualizar los cubos Parquet en el repositorio:

1. En tu repositorio de GitHub, dirígete a:
   **Settings** -> **Actions** -> **General**.
2. Desplázate hacia abajo hasta la sección **Workflow permissions**.
3. Selecciona la opción **Read and write permissions**.
4. Haz clic en **Save**.

### Probar el Pipeline Manualmente:
1. En GitHub, ve a la pestaña **Actions**.
2. En la lista izquierda, selecciona **Monthly SEPS ETL Pipeline & Verification**.
3. Haz clic en el botón desplegable **Run workflow** -> **Run workflow**.
4. El job descargará balances de la SEPS, validará la integridad matemática de los cubos Parquet con DuckDB y, si hay nuevos datos, hará commit a `master`, provocando un despliegue instantáneo y automático en Vercel.

---

## 5. Resumen de Cuotas y Costos

| Servicio | Nivel | Límite Gratuito | Consumo Estimado del Sistema |
| :--- | :--- | :--- | :--- |
| **Vercel** | Hobby | 100 GB ancho de banda / mes, 100k ejecuciones serverless | < 2 GB / mes (~2% del límite) |
| **Supabase** | Free | 500 MB base de datos PostgreSQL | < 10 MB (miles de usuarios y logs) |
| **GitHub Actions** | Free | 2,000 minutos de cómputo / mes | ~10 minutos / mes (< 0.5% del límite) |
| **Costo Total** | **$0.00 USD / mes** | **Perpetuo** | **100% Gratuito** |
