from fastapi import APIRouter, Depends, Body
from backend.app.core.security import require_roles
from backend.app.models.schemas import PipelineStatusResponse
from backend.app.services.mart_provider import mart_provider

router = APIRouter(prefix="/admin", tags=["Admin"])

auditor_or_admin = require_roles(["auditor", "administrador", "admin"])
admin_only = require_roles(["administrador", "admin"])

@router.get(
    "/pipeline-status",
    response_model=PipelineStatusResponse,
    operation_id="getPipelineStatus",
    summary="Consultar estado operativo del pipeline y Data Marts activos",
    description="Retorna el estado operativo del motor analítico DuckDB, versión del Data Mart activo, fecha de corte contable, periodos cubiertos y disponibilidad de datos en staging. Exclusivo para roles auditor y administrador.",
    dependencies=[Depends(auditor_or_admin)]
)
def get_pipeline_status():
    status = mart_provider.get_status()
    return PipelineStatusResponse(**status)

@router.post(
    "/pipeline-switch",
    summary="Ejecutar reemplazo atómico de Data Mart (Zero-Downtime Switch)",
    description="Conmuta en caliente el Data Mart activo hacia un directorio validado (ej. mart_staging o mart). Exclusivo para administradores.",
    dependencies=[Depends(admin_only)]
)
def post_pipeline_switch(
    target_dir: str = Body(default="mart_staging", embed=True, description="Nombre del directorio destino"),
    current_user: dict = Depends(admin_only)
):
    record = mart_provider.atomic_switch(
        new_dir_name=target_dir,
        trigger_user=current_user.get("sub", "admin")
    )
    return {
        "status": "success",
        "message": f"Data Mart conmutado exitosamente a '{target_dir}'.",
        "record": record,
        "pipeline_status": mart_provider.get_status()
    }
