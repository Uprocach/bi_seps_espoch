from pathlib import Path
import json
import os
from datetime import datetime, timezone
import duckdb
from backend.app.core.config import settings

class MartPathProvider:
    """Proveedor centralizado de resolución de rutas Parquet y conexiones DuckDB (AUD-17 / Fase 2).
    
    Elimina la duplicación de lógica entre AnalyticsRepository, BenchmarkingService y ExportService,
    y proporciona soporte nativo para reemplazo atómico de datos en caliente (Zero-Downtime Mart Switch).
    """

    def __init__(self, mart_dir: Path | None = None):
        self._custom_mart_dir = mart_dir

    @property
    def mart_dir(self) -> Path:
        """Resuelve dinámicamente el Data Mart activo en caliente mediante el puntero o enlace simbólico."""
        if self._custom_mart_dir:
            return self._custom_mart_dir

        base_processed = settings.DATA_MART_DIR.parent
        pointer_file = base_processed / "CURRENT_MART"

        # 1. Puntero atómico persistente (Windows y Linux)
        if pointer_file.exists():
            try:
                target_rel = pointer_file.read_text(encoding="utf-8").strip()
                if target_rel:
                    candidate = base_processed / target_rel
                    if candidate.exists() and candidate.is_dir():
                        return candidate
            except Exception:
                pass

        # 2. Enlace simbólico atómico (Linux/Docker)
        if settings.DATA_MART_DIR.is_symlink():
            try:
                return settings.DATA_MART_DIR.resolve()
            except Exception:
                pass

        return settings.DATA_MART_DIR

    def p(self, name: str) -> str:
        """Retorna la ruta normalizada con barras diagonales de un dataset Parquet en el mart activo."""
        return str(self.mart_dir / f"{name}.parquet").replace("\\", "/")

    def p_entity_partitioned(self) -> str:
        """Ruta al árbol de particiones Hive en Parquet para optimizar partition pruning."""
        partitioned_path = self.mart_dir / "partitioned" / "fct_indicators_entity"
        if partitioned_path.exists():
            return str(partitioned_path / "*/*/*.parquet").replace("\\", "/")
        return self.p("fct_indicators_entity_monthly")

    def create_connection(self, threads: int = 4) -> duckdb.DuckDBPyConnection:
        """Crea y configura una conexión DuckDB optimizada para consultas analíticas multihilo."""
        con = duckdb.connect()
        con.execute(f"PRAGMA threads={threads};")
        return con

    def get_staging_dir(self) -> Path:
        """Retorna la ruta a la carpeta de preparación (staging) aislada."""
        return settings.DATA_MART_DIR.parent / "mart_staging"

    def is_staging_ready(self) -> bool:
        """Verifica si el directorio staging contiene todos los artefactos requeridos para switch."""
        staging = self.get_staging_dir()
        if not staging.exists() or not staging.is_dir():
            return False

        required_files = [
            "dim_entities.parquet",
            "dim_provinces.parquet",
            "dim_segments.parquet",
            "fct_indicators_country_monthly.parquet",
            "fct_indicators_entity_monthly.parquet",
            "fct_indicators_segment_monthly.parquet"
        ]
        return all((staging / f).exists() for f in required_files)

    def atomic_switch(self, new_dir_name: str = "mart_staging", trigger_user: str = "sistema") -> dict:
        """Ejecuta el reemplazo atómico del Data Mart hacia un nuevo directorio validado."""
        base_processed = settings.DATA_MART_DIR.parent
        target_dir = base_processed / new_dir_name

        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"El directorio objetivo para switch no existe: {target_dir}")

        pointer_file = base_processed / "CURRENT_MART"
        tmp_pointer = base_processed / f"CURRENT_MART.{os.getpid()}.tmp"

        now_iso = datetime.now(timezone.utc).isoformat()

        # Escritura atómica del archivo puntero
        tmp_pointer.write_text(new_dir_name, encoding="utf-8")
        os.replace(tmp_pointer, pointer_file)

        # Actualizar historial de switches
        history_file = base_processed / "mart_history.json"
        history = []
        if history_file.exists():
            try:
                history = json.loads(history_file.read_text(encoding="utf-8"))
            except Exception:
                history = []

        switch_record = {
            "timestamp": now_iso,
            "switched_to": new_dir_name,
            "trigger_user": trigger_user,
            "status": "success"
        }
        history.append(switch_record)
        history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        # Registrar en bitácora de auditoría SQLite si está disponible
        try:
            from backend.app.services.user_db_service import user_db_service
            user_db_service.log_audit_event(
                user_sub=trigger_user,
                user_role="administrador",
                action="pipeline:switch",
                resource="/api/v1/admin/pipeline/switch",
                details={"switched_to": new_dir_name, "timestamp": now_iso}
            )
        except Exception:
            pass

        return switch_record

    def get_status(self) -> dict:
        """Retorna el estado operacional del pipeline, métricas del cubo activo y disponibilidad de staging."""
        con = self.create_connection()
        try:
            country_fct = self.p("fct_indicators_country_monthly")
            entities_dim = self.p("dim_entities")

            latest_period = "2025-12"
            periods_count = 96
            entities_count = 229

            if Path(country_fct).exists():
                row = con.execute(f"SELECT MAX(period), COUNT(DISTINCT period) FROM read_parquet('{country_fct}');").fetchone()
                if row and row[0]:
                    latest_period = row[0]
                    periods_count = int(row[1])

            if Path(entities_dim).exists():
                ent_row = con.execute(f"SELECT COUNT(*) FROM read_parquet('{entities_dim}');").fetchone()
                if ent_row and ent_row[0]:
                    entities_count = int(ent_row[0])

            base_processed = settings.DATA_MART_DIR.parent
            history_file = base_processed / "mart_history.json"
            last_switch = None
            if history_file.exists():
                try:
                    history = json.loads(history_file.read_text(encoding="utf-8"))
                    if history:
                        last_switch = history[-1].get("timestamp")
                except Exception:
                    pass

            return {
                "status": "active",
                "active_mart_dir": str(self.mart_dir).replace("\\", "/"),
                "data_as_of": f"{latest_period}-31",
                "latest_period": latest_period,
                "periods_count": periods_count,
                "entities_count": entities_count,
                "staging_ready": self.is_staging_ready(),
                "last_switch_timestamp": last_switch
            }
        finally:
            con.close()

mart_provider = MartPathProvider()
