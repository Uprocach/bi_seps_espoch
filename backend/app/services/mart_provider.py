from pathlib import Path
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict
import duckdb
from backend.app.core.config import settings

logger = logging.getLogger("mart_provider")

REQUIRED_MART_FILES = [
    "dim_provinces.parquet",
    "dim_segments.parquet",
    "dim_entities.parquet",
    "fct_indicators_entity_monthly.parquet",
    "fct_indicators_segment_monthly.parquet",
    "fct_indicators_country_monthly.parquet",
]


class MartValidationError(ValueError):
    """Error de dominio emitido cuando un Data Mart no supera el Gatekeeper Validador."""

    def __init__(self, report: Dict[str, Any]):
        self.report = report
        errors_str = "; ".join(report.get("errors", []))
        super().__init__(f"El Data Mart falló los controles de integridad: {errors_str}")


def verify_mart_integrity(target_dir: Path) -> Dict[str, Any]:
    """
    Función de verificación matemática e integridad pura sobre el Data Mart objetivo (Gatekeeper).
    Thread-safe, libre de mutaciones de variables de entorno y desacoplada de arneses unittest.
    """
    target_dir = Path(target_dir)
    report: Dict[str, Any] = {
        "is_valid": False,
        "target_dir": str(target_dir).replace("\\", "/"),
        "checked_files": [],
        "entities_count": 0,
        "periods_count": 0,
        "latest_period": "",
        "checks_passed": 0,
        "total_checks": 8,
        "errors": [],
    }

    missing = [f for f in REQUIRED_MART_FILES if not (target_dir / f).exists()]
    if missing:
        report["errors"].append(f"Archivos Parquet faltantes: {missing}")
        return report

    report["checked_files"] = list(REQUIRED_MART_FILES)
    report["checks_passed"] += 1

    con = duckdb.connect()
    try:
        paths = {f: str(target_dir / f).replace("\\", "/") for f in REQUIRED_MART_FILES}

        n_provinces = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_provinces.parquet']}')").fetchone()[0]
        n_segments = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_segments.parquet']}')").fetchone()[0]
        n_entities = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}')").fetchone()[0]
        report["entities_count"] = n_entities

        if n_provinces == 24 and n_segments == 6 and n_entities >= 200:
            report["checks_passed"] += 1
        else:
            report["errors"].append(
                f"Cardinalidad de dimensiones anómala (provincias: {n_provinces}, segmentos: {n_segments}, entidades: {n_entities})"
            )

        invalid_rucs = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}')
            WHERE length(ruc) != 13 OR NOT ruc LIKE '%001'
        """).fetchone()[0]
        null_provinces = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}')
            WHERE province_code IS NULL OR province_name IS NULL
        """).fetchone()[0]

        if invalid_rucs == 0 and null_provinces == 0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(
                f"Inconsistencia en dim_entities: {invalid_rucs} RUCs inválidos, {null_provinces} provincias nulas"
            )

        p_row = con.execute(
            f"SELECT COUNT(DISTINCT period), MAX(period) FROM read_parquet('{paths['fct_indicators_country_monthly.parquet']}')"
        ).fetchone()
        report["periods_count"] = p_row[0] if p_row else 0
        report["latest_period"] = p_row[1] if p_row else ""

        if report["periods_count"] > 0 and report["latest_period"]:
            report["checks_passed"] += 1
        else:
            report["errors"].append("Cero periodos registrados en fct_indicators_country_monthly")

        discrepancies = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{paths['fct_indicators_entity_monthly.parquet']}')
            WHERE denominator > 0
              AND value IS NOT NULL
              AND abs(value - round((numerator / denominator) * 100, 4)) > 0.001
        """).fetchone()[0]

        if discrepancies == 0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(
                f"Detectadas {discrepancies} discrepancias matemáticas en fórmula ratio = (num / den) * 100"
            )

        latest_p = report["latest_period"]
        reconciled = con.execute(f"""
            WITH ent AS (
                SELECT period, indicator_id, round(sum(numerator), 2) AS sum_num, round(sum(denominator), 2) AS sum_den
                FROM read_parquet('{paths['fct_indicators_entity_monthly.parquet']}')
                WHERE period = ? AND indicator_id = 'morosidad_cartera_total'
                  AND segment IN (
                      SELECT code FROM read_parquet('{paths['dim_segments.parquet']}')
                      WHERE reporting_frequency = 'monthly'
                  )
                GROUP BY period, indicator_id
            ),
            cty AS (
                SELECT period, indicator_id, numerator, denominator
                FROM read_parquet('{paths['fct_indicators_country_monthly.parquet']}')
                WHERE period = ? AND indicator_id = 'morosidad_cartera_total'
            )
            SELECT abs(ent.sum_num - cty.numerator), abs(ent.sum_den - cty.denominator)
            FROM ent JOIN cty ON ent.period = cty.period AND ent.indicator_id = cty.indicator_id
        """, [latest_p, latest_p]).fetchone()

        if reconciled and reconciled[0] <= 0.1 and reconciled[1] <= 0.1:
            report["checks_passed"] += 1
        else:
            report["errors"].append(f"Falla de reconciliación nacional en periodo {latest_p}: diferencias {reconciled}")

        morosidad_row = con.execute(f"""
            SELECT value FROM read_parquet('{paths['fct_indicators_country_monthly.parquet']}')
            WHERE period = ? AND indicator_id = 'morosidad_cartera_total'
        """, [latest_p]).fetchone()
        morosidad_val = morosidad_row[0] if morosidad_row and morosidad_row[0] is not None else -1

        if 4.0 <= morosidad_val <= 15.0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(f"Morosidad nacional fuera de rango plausible: {morosidad_val}%")

        seg4_active = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}') WHERE segment = 'SEGMENTO_4' AND is_active = TRUE"
        ).fetchone()[0]
        seg5_active = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}') WHERE segment = 'SEGMENTO_5' AND is_active = TRUE"
        ).fetchone()[0]

        if seg4_active > 0 and seg5_active > 0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(
                f"Faltan entidades activas en segmentos trimestrales (SEGMENTO_4={seg4_active}, SEGMENTO_5={seg5_active})"
            )

    except Exception as exc:
        report["errors"].append(f"Excepción durante la validación analítica: {str(exc)}")
    finally:
        con.close()

    report["is_valid"] = (report["checks_passed"] == report["total_checks"])
    return report

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

        return all((staging / f).exists() for f in REQUIRED_MART_FILES)

    def atomic_switch(
        self,
        new_dir_name: str = "mart_staging",
        trigger_user: str = "sistema",
        validate: bool = True,
    ) -> dict:
        """Ejecuta la validación Gatekeeper (por defecto) y el reemplazo atómico del Data Mart."""
        base_processed = settings.DATA_MART_DIR.parent
        target_dir = base_processed / new_dir_name

        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"El directorio objetivo para switch no existe: {target_dir}")

        validation_report: Dict[str, Any] | None = None
        if validate:
            validation_report = verify_mart_integrity(target_dir)
            if not validation_report["is_valid"]:
                raise MartValidationError(validation_report)

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
            "status": "success",
            "validation_report": validation_report,
        }
        history.append(switch_record)
        history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

        # Registrar en bitácora de auditoría mediante AuditTrail
        try:
            from backend.app.services.audit_service import audit_service
            audit_service.log_event(
                user_sub=trigger_user,
                user_role="administrador",
                action="pipeline:switch",
                resource="/api/v1/admin/pipeline/switch",
                details={"switched_to": new_dir_name, "timestamp": now_iso}
            )
        except Exception as e:
            logger.error(f"Error registrando auditoría de pipeline:switch ({new_dir_name}): {e}")

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
