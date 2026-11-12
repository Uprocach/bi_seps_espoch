from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.config import settings
from backend.app.core.security import CSRFOriginValidationMiddleware
from backend.app.core.errors import (
    APIProblemException,
    problem_exception_handler,
    validation_exception_handler,
    http_exception_handler
)
from backend.app.api.v1.metadata import router as metadata_router
from backend.app.api.v1.entities import router as entities_router
from backend.app.api.v1.indicators import router as indicators_router
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.supervision import router as supervision_router
from backend.app.api.v1.pro import router as pro_router
from backend.app.api.v1.admin_users import router as admin_users_router
from backend.app.api.v1.audit import router as audit_router
from backend.app.api.v1.admin_pipeline import router as admin_pipeline_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mitigación CSRF para sesiones basadas en cookies HttpOnly (AUD-03)
app.add_middleware(CSRFOriginValidationMiddleware)

# Registrar Manejadores de Excepciones RFC 9457 (Problem Details)
app.add_exception_handler(APIProblemException, problem_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# Registrar Routers de la API v1
app.include_router(metadata_router, prefix=settings.API_V1_STR)
app.include_router(entities_router, prefix=settings.API_V1_STR)
app.include_router(indicators_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(supervision_router, prefix=settings.API_V1_STR)
app.include_router(pro_router, prefix=settings.API_V1_STR)
app.include_router(admin_users_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(admin_pipeline_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
