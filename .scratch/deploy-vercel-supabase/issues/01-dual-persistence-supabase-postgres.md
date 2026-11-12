# Ticket 01: Capa de Persistencia Dual (PostgreSQL Supabase + SQLite Fallback)

Status: resolved
Blocked by: none

## Descripción
1. Agregar `psycopg[binary]>=3.1.0` a `requirements.txt`.
2. Actualizar `backend/app/core/config.py` para incluir el atributo `DATABASE_URL: str | None = None`.
3. Refactorizar `backend/app/services/user_db_service.py`:
   - Detectar si `DATABASE_URL` inicia con `postgres://` o `postgresql://`.
   - Si es PostgreSQL: conectar vía `psycopg`, inicializar esquemas `users` y `audit_logs` con sintaxis compatible (`SERIAL PRIMARY KEY`, `%s` como placeholders), y mapear resultados a diccionarios.
   - Si no está definida: mantener la conexión `sqlite3` actual hacia `data/users.db` con placeholders `?`.
4. Refactorizar `backend/app/services/audit_service.py` para usar la misma capa agnóstica de conexión.
5. Auto-sembrar el usuario `admin` inicial si no existe en la base de datos de forma idempotente.
6. Crear prueba unitaria en `backend/tests/test_dual_persistence.py` que valide el fallback transparente y la inicialización.

## Criterios de Aceptación
1. Con `DATABASE_URL` ausente, todos los tests existentes de usuarios y auditoría pasan 100% en SQLite.
2. La capa ejecuta consultas compatibles con PostgreSQL cuando `DATABASE_URL` está presente.
3. Se garantiza la creación de índices y siembra de `admin` en primer arranque.
