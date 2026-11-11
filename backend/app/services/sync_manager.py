"""
Gestor de Sincronización Web SEPS y Pipeline en Segundo Plano (ESPOCH-DI-060)
Controla el ciclo de vida asíncrono del rastreo, extracción, validación Gatekeeper y conmutación atómica.
"""

import os
import sys
import threading
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from backend.app.core.config import settings
from backend.app.models.schemas import PipelineSyncStatusResponse
from backend.app.services.audit_service import audit_service
from backend.app.services.mart_provider import mart_provider

logger = logging.getLogger("sync_manager")

class SyncManager:
    """Manejador concurrente y seguro para la sincronización del portal SEPS."""

    def __init__(self):
        self._lock = threading.Lock()
        self._is_running = False
        self._status: str = "idle"
        self._progress_percent: int = 100
        self._message: str = "Sistema listo para sincronización con el portal SEPS."
        self._detected_period: Optional[str] = None
        self._last_sync_timestamp: Optional[str] = None
        self._error_message: Optional[str] = None

    def get_status(self) -> PipelineSyncStatusResponse:
        """Retorna una instantánea del estado actual de la sincronización."""
        with self._lock:
            # Obtener el último periodo activo del mart si no se ha detectado uno nuevo
            period = self._detected_period
            if not period:
                mart_stat = mart_provider.get_status()
                period = mart_stat.get("latest_period")

            return PipelineSyncStatusResponse(
                status=self._status,
                progress_percent=self._progress_percent,
                message=self._message,
                detected_period=period,
                last_sync_timestamp=self._last_sync_timestamp,
                error_message=self._error_message or ""
            )

    def is_active(self) -> bool:
        """Indica si una tarea de sincronización se encuentra en ejecución."""
        with self._lock:
            return self._is_running

    def _update_progress(self, status: str, percent: int, message: str, period: Optional[str] = None):
        with self._lock:
            self._status = status
            self._progress_percent = min(100, max(0, percent))
            self._message = message
            if period:
                self._detected_period = period

    def run_sync_task(self, force: bool = False, trigger_user: str = "admin"):
        """
        Ejecuta el flujo completo de sincronización en segundo plano:
        1. Crawler web SEPS (descarga B11 y patrimonio técnico a data/interim).
        2. Construcción del Data Mart en mart_staging.
        3. Validación matemática estricta con test_marts.py.
        4. Reemplazo atómico (atomic_switch) hacia mart_staging.
        5. Bitácora forense de auditoría.
        """
        with self._lock:
            if self._is_running:
                logger.warning("Intento de iniciar sincronización mientras otra tarea está en curso.")
                return
            self._is_running = True
            self._status = "downloading"
            self._progress_percent = 5
            self._message = "Iniciando rastreador web SEPS..."
            self._error_message = None

        iso_start = datetime.now(timezone.utc).isoformat()
        try:
            from etl.seps_crawler import seps_crawler
            from etl.monthly_pipeline import validate_mart_dir

            # 1. Crawler Web SEPS
            def crawler_cb(stage: str, percent: int, msg: str):
                self._update_progress(stage, percent, msg)

            crawler_result = seps_crawler.sync(force=force, progress_callback=crawler_cb)
            latest_year = crawler_result.get("latest_web_year", 2026)
            detected_period = f"{latest_year}-08"

            if crawler_result.get("status") == "already_up_to_date" and not force:
                with self._lock:
                    self._status = "idle"
                    self._progress_percent = 100
                    self._message = f"El sistema ya está al día con la información más reciente de la SEPS ({latest_year})."
                    self._last_sync_timestamp = datetime.now(timezone.utc).isoformat()
                    self._is_running = False

                audit_service.log_event(
                    user_sub=trigger_user,
                    user_role="administrador",
                    action="pipeline_sync_noop",
                    resource="seps_crawler",
                    details={"latest_year": latest_year, "status": "already_up_to_date"}
                )
                return

            # 2. Construcción en mart_staging
            self._update_progress("extracting", 65, "Construyendo cubos analíticos en mart_staging...")
            staging_dir = settings.DATA_MART_DIR.parent / "mart_staging"
            staging_dir.mkdir(parents=True, exist_ok=True)

            os.environ["MART_DIR"] = str(staging_dir)
            from etl.build_marts import build_marts
            build_marts()

            # 3. Gatekeeper Validator
            self._update_progress("validating", 85, "Ejecutando validaciones matemáticas y de integridad...")
            is_valid = validate_mart_dir(staging_dir)

            if not is_valid:
                raise RuntimeError("El Data Mart en mart_staging no superó el 100% de los controles de integridad matemática.")

            # 4. Atomic Switch a producción
            self._update_progress("validating", 95, "Ejecutando reemplazo atómico Zero-Downtime a producción...")
            switch_record = mart_provider.atomic_switch(
                new_dir_name="mart_staging",
                trigger_user=trigger_user
            )

            # 5. Finalización exitosa
            now_iso = datetime.now(timezone.utc).isoformat()
            with self._lock:
                self._status = "success"
                self._progress_percent = 100
                self._message = f"Sincronización y switch atómico completados con éxito. Periodo {detected_period} activo."
                self._detected_period = detected_period
                self._last_sync_timestamp = now_iso
                self._is_running = False

            audit_service.log_event(
                user_sub=trigger_user,
                user_role="administrador",
                action="pipeline_sync_success",
                resource="data_mart",
                details={
                    "period": detected_period,
                    "switch_record": switch_record,
                    "updated_files": crawler_result.get("updated_files", [])
                }
            )

        except Exception as exc:
            logger.exception("Error crítico durante la sincronización web SEPS")
            now_iso = datetime.now(timezone.utc).isoformat()
            err_msg = str(exc)
            with self._lock:
                self._status = "failed"
                self._progress_percent = 100
                self._message = f"Fallo en la sincronización: {err_msg}"
                self._error_message = err_msg
                self._last_sync_timestamp = now_iso
                self._is_running = False

            audit_service.log_event(
                user_sub=trigger_user,
                user_role="administrador",
                action="pipeline_sync_failure",
                resource="seps_crawler",
                details={"error": err_msg, "started_at": iso_start}
            )

sync_manager = SyncManager()
