from pathlib import Path
import os

class Settings:
    PROJECT_NAME: str = "Sistema de Indicadores Financieros SFPS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_MART_DIR: Path = Path(os.getenv("DATA_MART_DIR", str(BASE_DIR / "data" / "processed" / "mart")))
    INDICATORS_SPEC_PATH: Path = Path(os.getenv("INDICATORS_SPEC_PATH", str(BASE_DIR / "config" / "indicators_spec.json")))
    OPENAPI_SPEC_PATH: Path = Path(os.getenv("OPENAPI_SPEC_PATH", str(BASE_DIR / "contracts" / "openapi.yaml")))
    CAMEL_THRESHOLDS_PATH: Path = Path(os.getenv("CAMEL_THRESHOLDS_PATH", str(BASE_DIR / "backend" / "app" / "config" / "camel_thresholds.json")))
    
    # Base de Datos y Supabase
    DATABASE_URL: str | None = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    SUPABASE_JWT_SECRET: str | None = os.getenv("SUPABASE_JWT_SECRET")
    
    # Seguridad JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "espoch-sfps-secret-key-di060-2026")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
    
    # Cookies de Sesión Segura (HttpOnly)
    COOKIE_NAME: str = "espoch_pro_access_token"
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() in ("true", "1")
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "lax")
    COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN")
    
    # Credenciales Institucionales ESPOCH (Mitigación NUEVA-01 y Roles RBAC)
    ACCREDITED_USER: str = os.getenv("ACCREDITED_USER", "investigador.espoch")
    ACCREDITED_PASSWORD: str = os.getenv("ACCREDITED_PASSWORD", "EspochPro2026#")
    AUDITOR_USER: str = os.getenv("AUDITOR_USER", "auditor.espoch")
    AUDITOR_PASSWORD: str = os.getenv("AUDITOR_PASSWORD", "EspochAuditor2026#")
    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin.espoch")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "EspochAdmin2026#")
    
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]

settings = Settings()
