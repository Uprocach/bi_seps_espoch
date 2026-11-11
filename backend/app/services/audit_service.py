import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("audit")

class AuditService:
    """Servicio de registro y trazabilidad de eventos de acceso y descarga de microdatos (RBAC y Compliance)."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.local_audit_log = settings.BASE_DIR / "data" / "interim" / "audit_events.jsonl"
        self._ensure_local_audit_dir()

    def _ensure_local_audit_dir(self):
        try:
            self.local_audit_log.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def log_event(
        self,
        user_sub: str,
        user_role: str,
        action: str,
        resource: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> dict:
        """Registra un evento de auditoría de manera no bloqueante con persistencia local inmediata (SQLite y JSONL) y réplica asíncrona a Supabase."""
        iso_now = datetime.now(timezone.utc).isoformat()
        event = {
            "timestamp": iso_now,
            "user_sub": user_sub,
            "user_role": user_role,
            "action": action,
            "resource": resource,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent
        }

        # 1. Persistencia transaccional en SQLite (users.db montado en volumen Docker - AUD-13)
        try:
            from backend.app.services.user_db_service import user_db
            user_db.insert_audit_log(
                timestamp=iso_now,
                user_sub=user_sub,
                user_role=user_role,
                action=action,
                resource=resource,
                details_json=json.dumps(details or {}, ensure_ascii=False),
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error registrando auditoría en SQLite: {e}")

        # 2. Persistencia local complementaria en archivo JSONL
        try:
            with open(self.local_audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error crítico escribiendo log de auditoría local JSONL: {e}")

        # 3. Replicación a Supabase en hilo desacoplado (evita agotar el threadpool de FastAPI ante latencias de red)
        if self.supabase_url and self.supabase_key:
            def _async_post():
                try:
                    headers = {
                        "apikey": self.supabase_key,
                        "Authorization": f"Bearer {self.supabase_key}",
                        "Content-Type": "application/json",
                        "Prefer": "return=minimal"
                    }
                    with httpx.Client(timeout=1.5) as client:
                        client.post(
                            f"{self.supabase_url.rstrip('/')}/rest/v1/audit_logs",
                            headers=headers,
                            json=event
                        )
                except Exception as e:
                    logger.warning(f"Fallo asíncrono al registrar evento en Supabase ({e}).")

            threading.Thread(target=_async_post, daemon=True).start()

        return event

    def query_events(
        self,
        limit: int = 50,
        offset: int = 0,
        user_sub: str | None = None,
        action: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> tuple[list[dict], int]:
        """Consulta la bitácora de auditoría forense persistida con filtros y paginación (AUD-14)."""
        from backend.app.services.user_db_service import user_db
        return user_db.list_audit_logs(
            limit=limit,
            offset=offset,
            user_sub=user_sub,
            action=action,
            start_date=start_date,
            end_date=end_date
        )

# Singleton del servicio de auditoría
audit_service = AuditService()
