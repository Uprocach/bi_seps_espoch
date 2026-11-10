from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Query, Response
from backend.app.core.security import require_roles, normalize_role, get_current_user
from backend.app.models.schemas import (
    AdminUserListItem,
    AdminUsersListResponse,
    AdminUserCreateRequest,
    AdminUserResetPasswordResponse,
    BulkImportRequest,
    BulkImportResponse
)
from backend.app.services.user_db_service import user_db
from backend.app.services.audit_service import audit_service

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])

admin_required = require_roles(["administrador", "admin"])

@router.get(
    "",
    response_model=AdminUsersListResponse,
    summary="Listar usuarios acreditados (Panel Administrador)",
    dependencies=[Depends(admin_required)]
)
def list_users(
    search: str | None = Query(default=None, description="Buscar por nombre, correo o usuario"),
    role: str | None = Query(default=None, description="Filtrar por rol"),
    is_active: bool | None = Query(default=None, description="Filtrar por estado activo/inactivo")
):
    users_raw = user_db.list_users(search=search, role=role, is_active=is_active)
    items = [
        AdminUserListItem(
            id=u["id"],
            username=u["username"],
            email=u["email"],
            full_name=u["full_name"],
            role=normalize_role(u["role"]), # type: ignore
            is_active=bool(u["is_active"]),
            must_change_password=bool(u["must_change_password"]),
            created_at=u["created_at"],
            last_login_at=u.get("last_login_at")
        )
        for u in users_raw
    ]
    return AdminUsersListResponse(users=items, total=len(items))

@router.post(
    "",
    response_model=AdminUserListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un usuario institucional individual",
    dependencies=[Depends(admin_required)]
)
def create_user(
    req: AdminUserCreateRequest,
    admin: Annotated[dict, Depends(get_current_user)]
):
    existing = user_db.get_user_by_username_or_email(req.username) or user_db.get_user_by_username_or_email(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El usuario '{req.username}' o el correo '{req.email}' ya existe en el sistema."
        )

    created = user_db.create_user(
        username=req.username,
        email=req.email,
        full_name=req.full_name,
        role=req.role,
        raw_password=req.initial_password,
        must_change_password=True
    )

    audit_service.log_event(
        user_sub=admin.get("sub", "admin"),
        user_role="administrador",
        action="admin:create_user",
        resource=f"/api/v1/admin/users/{created['id']}",
        details={"created_username": req.username, "role": req.role}
    )

    return AdminUserListItem(
        id=created["id"],
        username=created["username"],
        email=created["email"],
        full_name=created["full_name"],
        role=normalize_role(created["role"]), # type: ignore
        is_active=bool(created["is_active"]),
        must_change_password=bool(created["must_change_password"]),
        created_at=created["created_at"],
        last_login_at=created.get("last_login_at")
    )

@router.post(
    "/bulk-import",
    response_model=BulkImportResponse,
    summary="Importación masiva de usuarios acreditados (hasta 100+)",
    dependencies=[Depends(admin_required)]
)
def bulk_import(
    req: BulkImportRequest,
    admin: Annotated[dict, Depends(get_current_user)]
):
    raw_items = [u.model_dump() for u in req.users]
    created, errors = user_db.bulk_import_users(raw_items)

    audit_service.log_event(
        user_sub=admin.get("sub", "admin"),
        user_role="administrador",
        action="admin:bulk_import_users",
        resource="/api/v1/admin/users/bulk-import",
        details={"total_submitted": len(req.users), "imported": len(created), "errors_count": len(errors)}
    )

    return BulkImportResponse(
        imported_count=len(created),
        skipped_count=len(errors),
        created_users=created,
        errors=errors
    )

@router.post(
    "/{user_id}/reset-password",
    response_model=AdminUserResetPasswordResponse,
    summary="Restablecer contraseña de un usuario a clave temporal",
    dependencies=[Depends(admin_required)]
)
def reset_password(
    user_id: int,
    admin: Annotated[dict, Depends(get_current_user)]
):
    target_user = user_db.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    # Restablecer por defecto al username institucional (ej. nombre.apellido) con cambio obligatorio
    ok, temp_pwd = user_db.reset_password(user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo restablecer la contraseña.")

    audit_service.log_event(
        user_sub=admin.get("sub", "admin"),
        user_role="administrador",
        action="admin:reset_password",
        resource=f"/api/v1/admin/users/{user_id}",
        details={"target_username": target_user["username"]}
    )

    return AdminUserResetPasswordResponse(
        user_id=user_id,
        username=target_user["username"],
        temp_password=temp_pwd,
        message=f"Contraseña restablecida exitosamente a '{temp_pwd}'. El usuario deberá cambiarla obligatoriamente en su próximo inicio de sesión."
    )

@router.patch(
    "/{user_id}/toggle-active",
    response_model=AdminUserListItem,
    summary="Activar o desactivar cuenta de usuario",
    dependencies=[Depends(admin_required)]
)
def toggle_user_active(
    user_id: int,
    admin: Annotated[dict, Depends(get_current_user)]
):
    target = user_db.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    if target["username"] == admin.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta de administrador en sesión activa."
        )

    new_state = not bool(target["is_active"])
    user_db.toggle_user_active(user_id, new_state)
    updated = user_db.get_user_by_id(user_id)

    audit_service.log_event(
        user_sub=admin.get("sub", "admin"),
        user_role="administrador",
        action="admin:toggle_active",
        resource=f"/api/v1/admin/users/{user_id}",
        details={"username": target["username"], "is_active": new_state}
    )

    return AdminUserListItem(
        id=updated["id"],
        username=updated["username"],
        email=updated["email"],
        full_name=updated["full_name"],
        role=normalize_role(updated["role"]), # type: ignore
        is_active=bool(updated["is_active"]),
        must_change_password=bool(updated["must_change_password"]),
        created_at=updated["created_at"],
        last_login_at=updated.get("last_login_at")
    )

@router.get(
    "/template-csv",
    summary="Descargar plantilla CSV para importación masiva de usuarios",
    dependencies=[Depends(admin_required)]
)
def download_template_csv():
    csv_content = "nombre_completo,email,rol\nJuan Perez,juan.perez@espoch.edu.ec,investigador\nMaria Lopez,maria.lopez@espoch.edu.ec,auditor\nCarlos Ramos,carlos.ramos@espoch.edu.ec,investigador\n"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=plantilla_usuarios_sfps.csv"}
    )
