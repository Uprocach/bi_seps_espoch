import json
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from backend.app.core.security import require_roles, normalize_role
from backend.app.models.schemas import AuditLogItem, AuditLogsListResponse
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/admin/audit-logs", tags=["Audit"])

auditor_or_admin = require_roles(["auditor", "administrador", "admin"])

@router.get(
    "",
    response_model=AuditLogsListResponse,
    summary="Consultar bitácora de auditoría forense (Capa Pro / Compliance)",
    description="Permite a usuarios con rol auditor o administrador consultar y filtrar registros de auditoría forense.",
    dependencies=[Depends(auditor_or_admin)]
)
def list_audit_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Cantidad máxima de registros a retornar"),
    offset: int = Query(default=0, ge=0, description="Desplazamiento para paginación"),
    user_sub: str | None = Query(default=None, description="Filtrar por identificador de usuario"),
    action: str | None = Query(default=None, description="Filtrar por acción específica"),
    start_date: str | None = Query(default=None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="Fecha final (YYYY-MM-DD)")
):
    rows, total = audit_service.query_events(
        limit=limit,
        offset=offset,
        user_sub=user_sub,
        action=action,
        start_date=start_date,
        end_date=end_date
    )

    items = []
    for r in rows:
        details_val = {}
        if r.get("details_json"):
            try:
                details_val = json.loads(r["details_json"])
            except Exception:
                details_val = {"raw": r["details_json"]}

        items.append(
            AuditLogItem(
                id=r["id"],
                timestamp=r["timestamp"],
                user_sub=r["user_sub"],
                user_role=normalize_role(r["user_role"]),
                action=r["action"],
                resource=r["resource"],
                details=details_val,
                ip_address=r.get("ip_address"),
                user_agent=r.get("user_agent")
            )
        )

    return AuditLogsListResponse(
        logs=items,
        total=total,
        limit=limit,
        offset=offset
    )
