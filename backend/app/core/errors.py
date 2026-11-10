from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class APIProblemException(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        type_uri: str = "https://sistema-indicadores.local/problems/api-error",
        errors: list[dict] | None = None
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri
        self.errors = errors or []

async def problem_exception_handler(request: Request, exc: APIProblemException):
    problem = {
        "type": exc.type_uri,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": str(request.url.path),
    }
    if exc.errors:
        problem["errors"] = exc.errors
        
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json"
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg", "Invalid value")
        })
        
    problem = {
        "type": "https://sistema-indicadores.local/problems/validation-error",
        "title": "Error de validación",
        "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "detail": "Los parámetros enviados no cumplen con el contrato de la API.",
        "instance": str(request.url.path),
        "errors": errors
    }
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem,
        media_type="application/problem+json"
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    title_map = {
        400: "Parámetro inválido",
        404: "Recurso no encontrado",
        422: "Error de validación",
        500: "Internal Server Error"
    }
    problem = {
        "type": f"https://sistema-indicadores.local/problems/{exc.status_code}",
        "title": title_map.get(exc.status_code, "HTTP Error"),
        "status": exc.status_code,
        "detail": str(exc.detail),
        "instance": str(request.url.path),
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=problem,
        media_type="application/problem+json"
    )
