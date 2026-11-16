import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.services.dual_db import DualDatabaseAdapter, dual_db

logger = logging.getLogger("audit")


class AuditService:
    """
    Costura única de trazabilidad forense (`AuditTrail`) respaldada por DualDatabaseAdapter.
    Política fail-open en escritura: registra cualquier fallo en logs sin tumbar la operación principal.
    """

    def __init__(self, adapter: DualDatabaseAdapter | None = None):
        self.adapter = adapter or dual_db

    def log_event(
        self,
        user_sub: str,
        user_role: str,
        action: str,
        resource: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Registra un evento de auditoría en `audit_logs` mediante la Capa de Persistencia Dual."""
        iso_now = datetime.now(timezone.utc).isoformat()
        payload = details or {}
        event = {
            "timestamp": iso_now,
            "user_sub": user_sub,
            "user_role": user_role,
            "action": action,
            "resource": resource,
            "details": payload,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        sql_base = """
            INSERT INTO audit_logs
            (timestamp, user_sub, user_role, action, resource, details_json, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            iso_now,
            user_sub,
            user_role,
            action,
            resource,
            json.dumps(payload, ensure_ascii=False),
            ip_address,
            user_agent,
        )

        try:
            with self.adapter.connection() as conn:
                cursor = conn.cursor()
                self.adapter.execute_insert(cursor, sql_base, params)
        except Exception as e:
            logger.error(f"Error registrando evento de auditoría ({action}): {e}")

        return event

    def query_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_sub: str | None = None,
        action: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[dict], int]:
        """Consulta la bitácora de auditoría forense persistida con filtros y paginación (AUD-14)."""
        with self.adapter.connection() as conn:
            cursor = conn.cursor()
            where_clauses = ["1=1"]
            params: list[Any] = []

            if user_sub:
                where_clauses.append("LOWER(user_sub) LIKE ?")
                params.append(f"%{user_sub.strip().lower()}%")

            if action:
                where_clauses.append("action = ?")
                params.append(action.strip())

            if start_date:
                where_clauses.append("timestamp >= ?")
                params.append(start_date.strip())

            if end_date:
                val = end_date.strip()
                if len(val) == 10:
                    val += "T23:59:59"
                where_clauses.append("timestamp <= ?")
                params.append(val)

            where_str = " AND ".join(where_clauses)

            count_sql = self.adapter.prepare_sql(f"SELECT COUNT(*) AS cnt FROM audit_logs WHERE {where_str};")
            cursor.execute(count_sql, params)
            row = cursor.fetchone()
            total = row["cnt"] if isinstance(row, dict) else row[0]

            query = f"""
                SELECT id, timestamp, user_sub, user_role, action, resource, details_json, ip_address, user_agent
                FROM audit_logs
                WHERE {where_str}
                ORDER BY id DESC
                LIMIT ? OFFSET ?;
            """
            cursor.execute(self.adapter.prepare_sql(query), params + [limit, offset])
            rows = cursor.fetchall()
            return [dict(r) for r in rows], total


AuditTrail = AuditService
audit_service = AuditService(adapter=dual_db)
