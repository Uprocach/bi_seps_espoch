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
from pathlib import Path
from typing import Dict, Any, List
import duckdb

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

def verify_mart_integrity(target_dir: Path) -> Dict[str, Any]:
    """
    Función de verificación matemática e integridad pura sobre el Data Mart objetivo (Gatekeeper).
    Thread-safe, libre de mutaciones de variables de entorno y desacoplada de arneses unittest.
    """
    target_dir = Path(target_dir)
    required_files = [
        "dim_provinces.parquet",
        "dim_segments.parquet",
        "dim_entities.parquet",
        "fct_indicators_entity_monthly.parquet",
        "fct_indicators_segment_monthly.parquet",
        "fct_indicators_country_monthly.parquet"
    ]

    report: Dict[str, Any] = {
        "is_valid": False,
        "target_dir": str(target_dir).replace("\\", "/"),
        "checked_files": [],
        "entities_count": 0,
        "periods_count": 0,
        "latest_period": "",
        "checks_passed": 0,
        "total_checks": 7,
        "errors": []
    }

    # 1. Comprobar existencia física de archivos Parquet requeridos
    missing = [f for f in required_files if not (target_dir / f).exists()]
    if missing:
        report["errors"].append(f"Archivos Parquet faltantes: {missing}")
        return report

    report["checked_files"] = required_files
    report["checks_passed"] += 1  # Check 1: Archivos existentes

    con = duckdb.connect()
    try:
        paths = {f: str(target_dir / f).replace("\\", "/") for f in required_files}

        # Check 2: Dimensiones cargadas y cardinalidad mínima
        n_provinces = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_provinces.parquet']}')").fetchone()[0]
        n_segments = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_segments.parquet']}')").fetchone()[0]
        n_entities = con.execute(f"SELECT COUNT(*) FROM read_parquet('{paths['dim_entities.parquet']}')").fetchone()[0]
        report["entities_count"] = n_entities

        if n_provinces == 24 and n_segments >= 5 and n_entities >= 200:
            report["checks_passed"] += 1
        else:
            report["errors"].append(f"Cardinalidad de dimensiones anómala (provincias: {n_provinces}, segmentos: {n_segments}, entidades: {n_entities})")

        # Check 3: Integridad referencial de RUCs y provincias
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
            report["errors"].append(f"Inconsistencia en dim_entities: {invalid_rucs} RUCs inválidos, {null_provinces} provincias nulas")

        # Check 4: Periodos contables registrados
        p_row = con.execute(f"SELECT COUNT(DISTINCT period), MAX(period) FROM read_parquet('{paths['fct_indicators_country_monthly.parquet']}')").fetchone()
        report["periods_count"] = p_row[0] if p_row else 0
        report["latest_period"] = p_row[1] if p_row else ""

        if report["periods_count"] > 0 and report["latest_period"]:
            report["checks_passed"] += 1
        else:
            report["errors"].append("Cero periodos registrados en fct_indicators_country_monthly")

        # Check 5: Consistencia matemática de ratios individuales
        discrepancies = con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{paths['fct_indicators_entity_monthly.parquet']}')
            WHERE denominator > 0 
              AND value IS NOT NULL
              AND abs(value - round((numerator / denominator) * 100, 4)) > 0.001
        """).fetchone()[0]

        if discrepancies == 0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(f"Detectadas {discrepancies} discrepancias matemáticas en fórmula ratio = (num / den) * 100")

        # Check 6: Reconciliación matemática agregada a nivel nacional (Ratio de Sumas)
        latest_p = report["latest_period"]
        reconciled = con.execute(f"""
            WITH ent AS (
                SELECT period, indicator_id, round(sum(numerator), 2) AS sum_num, round(sum(denominator), 2) AS sum_den
                FROM read_parquet('{paths['fct_indicators_entity_monthly.parquet']}')
                WHERE period = ? AND indicator_id = 'morosidad_cartera_total'
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

        # Check 7: Rangos financieros normativos razonables (SEPS v3.0)
        morosidad_row = con.execute(f"""
            SELECT value FROM read_parquet('{paths['fct_indicators_country_monthly.parquet']}')
            WHERE period = ? AND indicator_id = 'morosidad_cartera_total'
        """, [latest_p]).fetchone()
        morosidad_val = morosidad_row[0] if morosidad_row and morosidad_row[0] is not None else -1

        if 4.0 <= morosidad_val <= 15.0:
            report["checks_passed"] += 1
        else:
            report["errors"].append(f"Morosidad nacional fuera de rango plausible: {morosidad_val}%")

    except Exception as exc:
        report["errors"].append(f"Excepción durante la validación analítica: {str(exc)}")
    finally:
        con.close()

    report["is_valid"] = (report["checks_passed"] == report["total_checks"])
    return report

def validate_mart_dir(target_dir: Path) -> bool:
    """Ejecuta la suite de verificación matemática y de integridad sobre el directorio objetivo."""
    print(f"[*] Validando integridad del Data Mart en: {target_dir}")
    report = verify_mart_integrity(target_dir)

    if report["is_valid"]:
        print(f"[+] Validación EXITOSA: {report['checks_passed']}/{report['total_checks']} controles aprobados en {target_dir}")
        print(f"    Último periodo: {report['latest_period']} ({report['periods_count']} meses, {report['entities_count']} entidades)")
        return True
    else:
        print(f"[!] ERROR DE VALIDACIÓN: {len(report['errors'])} fallas detectadas:")
        for err in report["errors"]:
            print(f"    - {err}")
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

    print("[*] Reconstruyendo cubos analíticos en mart_staging (parámetro explícito)...")
    build_marts(target_dir=staging_dir)

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
