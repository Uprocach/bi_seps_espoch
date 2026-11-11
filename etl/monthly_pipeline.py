"""
Pipeline de Datos Mensual: Orquestación y Reemplazo Atómico Zero-Downtime (Fase 2 / ESPOCH-DI-060)
Uso:
  python etl/monthly_pipeline.py --status
  python etl/monthly_pipeline.py --validate [dir_name]
  python etl/monthly_pipeline.py --switch [dir_name]
  python etl/monthly_pipeline.py --rollback
"""

import sys
import os
import argparse
import unittest
from pathlib import Path

# Asegurar path del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.app.services.mart_provider import mart_provider
from backend.app.core.config import settings

def print_status():
    """Muestra el estado actual del Data Mart y el pipeline."""
    status = mart_provider.get_status()
    print("=" * 60)
    print("ESTADO DEL PIPELINE DE DATOS (ESPOCH-DI-060)")
    print("=" * 60)
    print(f"  Estado general:          {status['status']}")
    print(f"  Directorio activo:       {status['active_mart_dir']}")
    print(f"  Periodo más reciente:    {status['latest_period']} (Corte: {status['data_as_of']})")
    print(f"  Periodos procesados:     {status['periods_count']} meses")
    print(f"  Entidades registradas:   {status['entities_count']} cooperativas/mutualistas")
    print(f"  Staging listo:           {'SÍ' if status['staging_ready'] else 'NO'}")
    print(f"  Último switch atómico:   {status['last_switch_timestamp'] or 'Inicial (sin switches)'}")
    print("=" * 60)

def validate_mart_dir(target_dir: Path) -> bool:
    """Ejecuta la suite de verificación matemática y de integridad sobre el directorio objetivo."""
    print(f"[*] Validando integridad del Data Mart en: {target_dir}")
    os.environ["MART_DIR"] = str(target_dir)

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(BASE_DIR / "etl"), pattern="test_marts.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print(f"[+] Validación EXITOSA: 100% de pruebas aprobadas en {target_dir}")
        return True
    else:
        print(f"[!] ERROR DE VALIDACIÓN: {len(result.failures)} fallas, {len(result.errors)} errores.")
        return False

def execute_switch(target_name: str = "mart_staging", trigger_user: str = "cli_admin"):
    """Ejecuta la validación y el reemplazo atómico del Data Mart."""
    target_path = settings.DATA_MART_DIR.parent / target_name

    if not target_path.exists():
        print(f"[!] Error: El directorio de datos '{target_path}' no existe.")
        sys.exit(1)

    # 1. Gatekeeper Validador
    if not validate_mart_dir(target_path):
        print("[!] Abortando switch atómico: los datos no superaron los controles de integridad.")
        sys.exit(1)

    # 2. Reemplazo Atómico
    print(f"[*] Ejecutando reemplazo atómico (Zero-Downtime Atomic Switch) hacia: {target_name}...")
    record = mart_provider.atomic_switch(new_dir_name=target_name, trigger_user=trigger_user)
    print(f"[+] Reemplazo completado con éxito a las {record['timestamp']}.")
    print_status()

def execute_rollback():
    """Revierte la partición activa al Data Mart base 'mart'."""
    print("[*] Revertiendo al Data Mart base por defecto ('mart')...")
    record = mart_provider.atomic_switch(new_dir_name="mart", trigger_user="rollback_admin")
    print(f"[+] Rollback completado a las {record['timestamp']}.")
    print_status()

def execute_sync_web(force: bool = False):
    """Ejecuta el crawler SEPS, reconstruye mart_staging, valida con Gatekeeper y conmuta a producción."""
    from etl.seps_crawler import seps_crawler
    from etl.build_marts import build_marts

    print("=" * 60)
    print("INICIANDO SINCRONIZACIÓN AUTOMATIZADA WEB SEPS")
    print("=" * 60)
    def cli_progress(stage, pct, msg):
        print(f"  [{stage.upper():10}] {pct:3}% -> {msg}")

    result = seps_crawler.sync(force=force, progress_callback=cli_progress)
    if result.get("status") == "already_up_to_date" and not force:
        print("[+] Los datos locales ya están al día con el portal SEPS.")
        print_status()
        return

    staging_dir = settings.DATA_MART_DIR.parent / "mart_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MART_DIR"] = str(staging_dir)

    print("[*] Reconstruyendo cubos analíticos en mart_staging...")
    build_marts()

    print("[*] Ejecutando validación y conmutación atómica...")
    execute_switch("mart_staging", trigger_user="monthly_pipeline_cli")

def main():
    parser = argparse.ArgumentParser(description="Orquestador de Pipeline Zero-Downtime ESPOCH-DI-060")
    parser.add_argument("--status", action="store_true", help="Consultar estado del Data Mart activo")
    parser.add_argument("--validate", nargs="?", const="mart", help="Validar directorio específico (default: mart)")
    parser.add_argument("--switch", nargs="?", const="mart_staging", help="Ejecutar switch atómico al directorio indicado")
    parser.add_argument("--rollback", action="store_true", help="Revertir al Data Mart base ('mart')")
    parser.add_argument("--sync-web", action="store_true", help="Sincronizar y descargar automáticamente datos desde el portal SEPS")
    parser.add_argument("--force", action="store_true", help="Forzar re-descarga aunque el año ya exista localmente")

    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.validate:
        target = settings.DATA_MART_DIR.parent / args.validate
        success = validate_mart_dir(target)
        sys.exit(0 if success else 1)
    elif args.switch:
        execute_switch(args.switch)
    elif args.rollback:
        execute_rollback()
    elif args.sync_web:
        execute_sync_web(force=args.force)
    else:
        print_status()

if __name__ == "__main__":
    main()
