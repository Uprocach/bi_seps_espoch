from fastapi import APIRouter, Depends, Body, BackgroundTasks, status
from fastapi.responses import JSONResponse
from backend.app.core.security import require_roles
from backend.app.models.schemas import (
    PipelineStatusResponse,
    PipelineSyncRequest,
    PipelineSyncStatusResponse
)
from backend.app.services.mart_provider import mart_provider
from backend.app.services.sync_manager import sync_manager

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
    status_data = mart_provider.get_status()
    return PipelineStatusResponse(**status_data)

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

@router.post(
    "/pipeline-sync",
    response_model=PipelineSyncStatusResponse,
    operation_id="triggerPipelineSync",
    summary="Disparar sincronización automatizada con el portal SEPS",
    description="Inicia la verificación y descarga desatendida de nuevos boletines contables B11 desde el portal oficial de estadísticas de la SEPS. Exclusivo para rol administrador.",
    dependencies=[Depends(admin_only)],
    responses={
        200: {"model": PipelineSyncStatusResponse, "description": "Modo directo, dry-run o sincronización previa en curso"},
        202: {"model": PipelineSyncStatusResponse, "description": "Sincronización en segundo plano aceptada"}
    }
)
def post_pipeline_sync(
    background_tasks: BackgroundTasks,
    request: PipelineSyncRequest = Body(default_factory=PipelineSyncRequest),
    current_user: dict = Depends(admin_only)
):
    if request.dry_run:
        from etl.seps_crawler import seps_crawler
        catalog = seps_crawler.discover_downloads()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=PipelineSyncStatusResponse(
                status="idle",
                progress_percent=100,
                message=f"Modo simulación (dry-run): portal SEPS dispone de datos hasta año {catalog['latest_year_available']}.",
                detected_period=f"{catalog['latest_year_available']}-08",
                last_sync_timestamp=None,
                error_message=""
            ).model_dump()
        )

    if sync_manager.is_active():
        current_st = sync_manager.get_status()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=current_st.model_dump()
        )

    background_tasks.add_task(
        sync_manager.run_sync_task,
        force=request.force,
        trigger_user=current_user.get("sub", "admin")
    )

    initial_status = PipelineSyncStatusResponse(
        status="downloading",
        progress_percent=10,
        message="Tarea de sincronización aceptada. Iniciando rastreo y descarga en segundo plano...",
        detected_period=None,
        last_sync_timestamp=None,
        error_message=""
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=initial_status.model_dump()
    )

@router.get(
    "/pipeline-sync-status",
    response_model=PipelineSyncStatusResponse,
    operation_id="getPipelineSyncStatus",
    summary="Consultar estado de la tarea de sincronización web SEPS",
    description="Retorna el avance y estado en vivo de la sincronización con el portal de la SEPS. Exclusivo para roles auditor y administrador.",
    dependencies=[Depends(auditor_or_admin)]
)
def get_pipeline_sync_status():
    return sync_manager.get_status()
