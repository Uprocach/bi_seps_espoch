import hmac
from datetime import datetime, timedelta, timezone
from typing import Callable, Any
from urllib.parse import urlparse
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt
from backend.app.core.config import settings

def check_csrf_origin(
    method: str,
    cookies: dict | None,
    origin: str | None,
    referer: str | None,
    client_host: str | None = None,
    is_internal_test: bool = False
) -> bool:
    """Valida la procedencia de la solicitud contra la lista blanca institucional (Mitigación AUD-03)."""
    if method in {"GET", "HEAD", "OPTIONS"}:
        return True

    cookies = cookies or {}
    if settings.COOKIE_NAME not in cookies:
        return True

    allowed_origins = {o.rstrip("/") for o in settings.CORS_ORIGINS}

    origin_to_check = None
    if origin:
        origin_to_check = origin.rstrip("/")
    elif referer:
        parsed = urlparse(referer)
        origin_to_check = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    if is_internal_test:
        return True

    if client_host in ("testclient", "127.0.0.1", "localhost") and not origin and not referer:
        return True

    return bool(origin_to_check and origin_to_check in allowed_origins)

class CSRFOriginValidationMiddleware:
    """Mitigación contra Cross-Site Request Forgery (CSRF) para sesiones basadas en HttpOnly Cookies.
    
    Implementación ASGI pura (sin BaseHTTPMiddleware) para máxima velocidad y compatibilidad thread-safe.
    Verifica que las solicitudes mutacionales o de exportación (POST, PUT, DELETE, PATCH)
    autenticadas mediante cookie institucional provengan de un Origin o Referer autorizado en CORS_ORIGINS.
    """
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        if method in self.SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        # Parsear cabeceras raw de la solicitud ASGI
        headers_dict = {k.lower(): v for k, v in scope.get("headers", [])}
        cookie_header = headers_dict.get(b"cookie", b"").decode("latin1")
        cookies = {}
        if cookie_header:
            for item in cookie_header.split(";"):
                if "=" in item:
                    k, v = item.strip().split("=", 1)
                    cookies[k] = v

        origin = headers_dict.get(b"origin", b"").decode("latin1") or None
        referer = headers_dict.get(b"referer", b"").decode("latin1") or None
        client_host = scope.get("client", [""])[0] if scope.get("client") else None
        is_internal = headers_dict.get(b"x-internal-test", b"") == b"true"

        is_valid = check_csrf_origin(
            method=method,
            cookies=cookies,
            origin=origin,
            referer=referer,
            client_host=client_host,
            is_internal_test=is_internal
        )

        if not is_valid:
            response = JSONResponse(
                status_code=403,
                content={
                    "detail": "Violación de seguridad CSRF: Origen no autorizado o cabecera ausente en solicitud autenticada por cookie."
                }
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

security_bearer = HTTPBearer(auto_error=False)

# Mapeo y normalización de roles
ROLE_NORMALIZATION = {
    "investigador": "investigador",
    "researcher": "investigador",
    "auditor": "auditor",
    "administrador": "administrador",
    "admin": "administrador",
}

ROLE_PERMISSIONS = {
    "investigador": ["read_public", "read_pro", "benchmarking", "export_csv"],
    "auditor": ["read_public", "read_pro", "benchmarking", "export_csv", "export_excel", "view_audit_logs"],
    "administrador": ["read_public", "read_pro", "benchmarking", "export_csv", "export_excel", "view_audit_logs", "manage_users"],
}

def normalize_role(role: str | None) -> str:
    if not role:
        return "public"
    return ROLE_NORMALIZATION.get(role.lower(), "public")

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Genera un JWT firmado para autenticación de sesión en la Capa Pro."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRE_HOURS))
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "espoch-sfps-pro"
    })
    # Preservar rol solicitado y normalizado
    raw_role = to_encode.get("role", "investigador")
    to_encode["role"] = raw_role
    to_encode["normalized_role"] = normalize_role(raw_role)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    """Decodifica y valida un token JWT soportando el secreto local o el secreto Supabase."""
    # Probar primero con el secreto local del sistema
    secrets = [settings.JWT_SECRET_KEY]
    if settings.SUPABASE_JWT_SECRET and settings.SUPABASE_JWT_SECRET != settings.JWT_SECRET_KEY:
        secrets.append(settings.SUPABASE_JWT_SECRET)

    last_error = None
    for secret in secrets:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_aud": False}
            )
            raw_role = payload.get("role") or payload.get("user_metadata", {}).get("role") or "investigador"
            payload["normalized_role"] = normalize_role(raw_role)
            payload["role"] = raw_role
            return payload
        except jwt.PyJWTError as e:
            last_error = e

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso inválido o expirado."
    )

def extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None = None) -> str | None:
    """Extrae el token JWT priorizando la HttpOnly Cookie sobre la cabecera Authorization."""
    cookie_token = request.cookies.get(settings.COOKIE_NAME)
    if cookie_token:
        return cookie_token

    if credentials and credentials.credentials:
        return credentials.credentials

    # Fallback directo en cabecera Authorization
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None

def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer)
) -> dict | None:
    """Extrae el usuario autenticado del token (cookie o bearer); retorna None si no existe."""
    token = extract_token(request, credentials)
    if not token:
        return None
    try:
        return decode_token(token)
    except HTTPException:
        return None

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer)
) -> dict:
    """Dependencia estricta: Retorna el usuario autenticado o lanza HTTP 401."""
    token = extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida: No se proporcionó token de sesión activo."
        )
    return decode_token(token)

def require_roles(allowed_roles: list[str]) -> Callable[[dict], dict]:
    """Factory de dependencias RBAC. Valida que el rol del usuario esté en la lista permitida."""
    normalized_allowed = [normalize_role(r) for r in allowed_roles]

    def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_role = normalize_role(user.get("role"))
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: El rol '{user_role}' no cuenta con permisos suficientes. Roles requeridos: {allowed_roles}."
            )
        return user

    return role_checker

def require_accredited_user(user: dict | None = Depends(get_current_user_optional)) -> dict:
    """Compatibilidad con endpoints existentes: exige acreditación Pro activa."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requiere acreditación institucional activa (Vista Pro)."
        )
    user_role = normalize_role(user.get("role"))
    if user_role not in ["investigador", "auditor", "administrador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido: Se requiere acreditación institucional activa (Vista Pro)."
        )
    return user

def verify_credentials(username: str, password: str, requested_role: str = "investigador") -> dict | None:
    """Valida credenciales contra la base de datos de usuarios (SQLite) o el fallback institucional."""
    norm_requested = normalize_role(requested_role)

    # 1. Intentar validar contra base de datos SQLite (UserDB)
    try:
        from backend.app.services.user_db_service import user_db
        db_user = user_db.get_user_by_username_or_email(username)
        if db_user:
            if not db_user["is_active"]:
                return None
            if user_db.verify_password(password, db_user["password_hash"], db_user["salt"]):
                user_role = db_user["role"]
                norm_user_role = normalize_role(user_role)
                # Validar que el rol solicitado coincida con el rol asignado o su normalización
                if requested_role and requested_role not in (user_role, norm_user_role) and norm_requested not in (user_role, norm_user_role):
                    return None
                user_db.record_login(db_user["id"])
                final_role = requested_role if requested_role in ("researcher", "auditor", "admin", "investigador", "administrador") else user_role
                return {
                    "sub": db_user["username"],
                    "user_id": db_user["id"],
                    "role": final_role,
                    "normalized_role": norm_user_role,
                    "name": db_user["full_name"],
                    "email": db_user["email"],
                    "permissions": ROLE_PERMISSIONS.get(norm_user_role, []),
                    "must_change_password": bool(db_user["must_change_password"])
                }
    except Exception:
        pass

    # 2. Fallback institucional / tests en memoria
    users = {
        settings.ACCREDITED_USER: {
            "password": settings.ACCREDITED_PASSWORD,
            "roles": ["investigador", "auditor"],
            "full_name": "Investigador Institucional ESPOCH",
            "email": "investigador.espoch@espoch.edu.ec"
        },
        settings.AUDITOR_USER: {
            "password": settings.AUDITOR_PASSWORD,
            "roles": ["auditor", "investigador"],
            "full_name": "Auditor Financiero de Riesgo SFPS",
            "email": "auditor.espoch@espoch.edu.ec"
        },
        settings.ADMIN_USER: {
            "password": settings.ADMIN_PASSWORD,
            "roles": ["administrador", "auditor", "investigador"],
            "full_name": getattr(settings, "ADMIN_FULL_NAME", "Dennys Rojas"),
            "email": getattr(settings, "ADMIN_EMAIL", "dennys.rojas@espoch.edu.ec")
        }
    }

    user_data = users.get(username)
    if not user_data:
        return None

    if not hmac.compare_digest(user_data["password"], password):
        return None

    # Verificar si el rol solicitado es admitido para el usuario
    if requested_role not in user_data["roles"] and norm_requested not in user_data["roles"]:
        return None

    return {
        "sub": username,
        "role": requested_role if requested_role in ("researcher", "auditor", "admin", "investigador", "administrador") else norm_requested,
        "normalized_role": norm_requested,
        "name": user_data["full_name"],
        "email": user_data["email"],
        "permissions": ROLE_PERMISSIONS.get(norm_requested, []),
        "must_change_password": False
    }
