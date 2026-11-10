from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Response, Request, Depends
from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    verify_credentials,
    get_current_user,
    get_current_user_optional,
    normalize_role,
    ROLE_PERMISSIONS
)
from backend.app.models.schemas import LoginRequest, UserResponse, ChangePasswordRequest
from backend.app.services.audit_service import audit_service
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Auth"])

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: str

@router.post(
    "/login",
    response_model=UserResponse,
    summary="Inicio de sesión institucional para la Capa Pro",
    description="Autentica las credenciales institucionales ESPOCH / Supabase e inyecta la HttpOnly Cookie segura de sesión."
)
def login(
    req: LoginRequest,
    response: Response,
    request: Request
):
    username = req.username or req.user or "investigador.espoch"
    user_payload = verify_credentials(username, req.password, req.role)
    if not user_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales institucionales incorrectas o rol no autorizado para el usuario."
        )

    # Generar token JWT con claims institucionales
    token = create_access_token(data=user_payload)

    # Inyección de HttpOnly Cookie (Seguridad Bancaria contra XSS)
    max_age_seconds = settings.JWT_EXPIRE_HOURS * 3600
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
        domain=settings.COOKIE_DOMAIN
    )

    # Registro de Auditoría
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit_service.log_event(
        user_sub=user_payload["sub"],
        user_role=user_payload["role"],
        action="auth:login",
        resource="/api/v1/auth/login",
        details={"login_type": "cookie_session"},
        ip_address=client_ip,
        user_agent=user_agent
    )

    must_change = bool(user_payload.get("must_change_password", False))

    return UserResponse(
        sub=user_payload["sub"],
        role=user_payload["role"],
        name=user_payload["name"],
        email=user_payload["email"],
        permissions=user_payload["permissions"],
        authenticated=True,
        must_change_password=must_change
    )

@router.post(
    "/logout",
    summary="Cierre de sesión seguro",
    description="Invalida la HttpOnly Cookie de sesión activa y registra el evento de salida en auditoría."
)
def logout(
    response: Response,
    request: Request,
    user: Annotated[dict | None, Depends(get_current_user_optional)] = None
):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        domain=settings.COOKIE_DOMAIN
    )

    if user:
        client_ip = request.client.host if request.client else None
        audit_service.log_event(
            user_sub=user.get("sub", "anonymous"),
            user_role=user.get("role", "public"),
            action="auth:logout",
            resource="/api/v1/auth/logout",
            details={},
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent")
        )

    return {"message": "Sesión institucional cerrada exitosamente.", "authenticated": False}

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Consultar perfil del usuario autenticado",
    description="Devuelve la identidad, rol normalizado y permisos del usuario a partir de la HttpOnly Cookie o Bearer token."
)
def get_me(user: Annotated[dict, Depends(get_current_user)]):
    role = normalize_role(user.get("role"))
    sub = user.get("sub", "investigador.espoch")
    must_change = bool(user.get("must_change_password", False))
    try:
        from backend.app.services.user_db_service import user_db
        db_u = user_db.get_user_by_username_or_email(sub)
        if db_u:
            must_change = bool(db_u["must_change_password"])
    except Exception:
        pass

    return UserResponse(
        sub=sub,
        role=role,
        name=user.get("name") or ("Investigador Institucional" if role == "investigador" else "Auditor SFPS" if role == "auditor" else "Administrador"),
        email=user.get("email") or f"{sub}@espoch.edu.ec",
        permissions=ROLE_PERMISSIONS.get(role, []),
        authenticated=True,
        must_change_password=must_change
    )

@router.post(
    "/change-password",
    response_model=UserResponse,
    summary="Cambio obligatorio o voluntario de contraseña",
    description="Permite al usuario autenticado actualizar su contraseña personal y quitar la marca de cambio obligatorio."
)
def change_password(
    req: ChangePasswordRequest,
    user: Annotated[dict, Depends(get_current_user)]
):
    from backend.app.services.user_db_service import user_db
    sub = user.get("sub")
    db_u = user_db.get_user_by_username_or_email(sub)
    if not db_u:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no registrado en la base de datos para actualización de contraseña."
        )

    if not user_db.verify_password(req.current_password, db_u["password_hash"], db_u["salt"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual ingresada es incorrecta."
        )

    user_db.update_password(db_u["id"], req.new_password)
    updated = user_db.get_user_by_id(db_u["id"])
    role = normalize_role(updated["role"])

    return UserResponse(
        sub=updated["username"],
        role=role,
        name=updated["full_name"],
        email=updated["email"],
        permissions=ROLE_PERMISSIONS.get(role, []),
        authenticated=True,
        must_change_password=False
    )

# Compatibilidad hacia atrás con endpoint legacy /token
@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtención de token JWT (Compatibilidad Legacy)",
    description="Genera el token Bearer y además setea la cookie segura de sesión."
)
def get_auth_token(
    req: LoginRequest,
    response: Response = Response(),
    request: Request = None
):
    user_login = req.username or req.user or "investigador.espoch"
    user_payload = verify_credentials(user_login, req.password, req.role)
    if not user_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales institucionales incorrectas o rol no autorizado.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = create_access_token(data=user_payload)
    
    # Inyectar también la cookie si hay objeto response
    if response is not None:
        max_age_seconds = settings.JWT_EXPIRE_HOURS * 3600
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=token,
            max_age=max_age_seconds,
            expires=max_age_seconds,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            path="/",
            domain=settings.COOKIE_DOMAIN
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": req.role if req.role in ["researcher", "auditor", "admin"] else user_payload["role"],
        "user": user_payload["sub"]
    }
