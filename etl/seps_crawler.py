"""
Motor de Rastreo y Descarga SEPS (Crawler & Extractor) - ESPOCH-DI-060
Automatiza el rastreo e ingesta periódica de balances B11 y patrimonio técnico (ACPR)
desde el portal oficial de estadísticas de la SEPS (WordPress Simple Download Monitor).
"""

import sys
import os
import re
import html as html_lib
import urllib.request
import zipfile
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

# Asegurar path del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import duckdb

PORTAL_URL = "https://estadisticas.seps.gob.ec/index.php/estadisticas-sfps/"
DOWNLOAD_BASE_URL = "https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id="

RAW_EEFF_DIR = BASE_DIR / "data" / "raw" / "Situación Financiera" / "Bases de Datos" / "Estados Financieros Mensuales"
RAW_PAT_DIR = BASE_DIR / "data" / "raw" / "Situación Financiera" / "Reportes" / "Patrimonio técnico"
INTERIM_EEFF_DIR = BASE_DIR / "data" / "interim" / "situacion_financiera" / "estados_financieros_mensuales"
INTERIM_PAT_DIR = BASE_DIR / "data" / "interim" / "patrimonio_tecnico"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (ESPOCH-DI-060 Bot)"

class SepsCrawler:
    """Motor de descubrimiento, descarga y transformación canónica de datos SEPS."""

    def __init__(self, portal_url: str = PORTAL_URL):
        self.portal_url = portal_url
        self.headers = {"User-Agent": USER_AGENT}

    def fetch_portal_html(self, timeout: int = 20) -> str:
        """Descarga el HTML crudo del portal de estadísticas SEPS."""
        req = urllib.request.Request(self.portal_url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")
        return html_lib.unescape(content)

    def discover_downloads(self) -> Dict[str, Any]:
        """
        Rastrea el portal e identifica los IDs de descarga de balances mensuales y patrimonio técnico.
        Retorna un catálogo estructurado con los periodos disponibles.
        """
        html = self.fetch_portal_html()
        pattern = re.compile(
            r'<a[^>]+href=["\']([^"\']*download_id=(\d+)[^"\']*)["\'][^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL
        )

        catalog: Dict[str, Any] = {
            "eeff_mensuales_bases": {},      # { año: download_id }
            "patrimonio_tecnico": {},        # { año: download_id }
            "eeff_mensuales_reportes": {},   # { año: download_id }
            "latest_year_available": 0,
            "total_links_found": 0
        }

        for match in pattern.finditer(html):
            catalog["total_links_found"] += 1
            href, d_id_str, text_raw = match.groups()
            d_id = int(d_id_str)
            text = re.sub(r'<[^>]+>', '', text_raw).strip()
            
            # Buscar año en el texto del enlace (ej: '2026', '2025', '2026 con corte al...')
            year_match = re.search(r'(20\d{2})', text)
            if not year_match:
                continue
            year = int(year_match.group(1))

            # Extraer contexto previo para determinar la sección exacta
            pos = match.start()
            prev_chunk = html[max(0, pos - 2000):pos].lower()

            if "patrimonio" in prev_chunk:
                if year not in catalog["patrimonio_tecnico"]:
                    catalog["patrimonio_tecnico"][year] = d_id
            elif "estados financieros mensuales" in prev_chunk:
                if "base" in prev_chunk:
                    if year not in catalog["eeff_mensuales_bases"]:
                        catalog["eeff_mensuales_bases"][year] = d_id
                else:
                    if year not in catalog["eeff_mensuales_reportes"]:
                        catalog["eeff_mensuales_reportes"][year] = d_id
                        catalog["eeff_mensuales_reportes"][year] = d_id

            if year > catalog["latest_year_available"]:
                catalog["latest_year_available"] = year

        return catalog

    def download_file(
        self,
        download_id: int,
        dest_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        timeout: int = 120
    ) -> Path:
        """
        Descarga un archivo por su download_id usando streaming atómico y verifica su integridad ZIP.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{DOWNLOAD_BASE_URL}{download_id}"
        req = urllib.request.Request(url, headers=self.headers)

        temp_dest = dest_path.with_suffix(".tmp")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1MB chunks

                with open(temp_dest, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            if not zipfile.is_zipfile(temp_dest):
                raise ValueError(f"El archivo descargado desde {url} no es un formato ZIP válido.")

            if dest_path.exists():
                dest_path.unlink()
            temp_dest.rename(dest_path)
            return dest_path
        finally:
            if temp_dest.exists():
                temp_dest.unlink()

    def extract_eeff_b11_to_parquet(
        self,
        zip_path: Path,
        output_parquet: Path
    ) -> Dict[str, Any]:
        """
        Extrae el archivo tabular B11 de un ZIP y genera un Parquet canónico de 7 columnas optimizado con DuckDB.
        """
        output_parquet.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir_path = Path(tmpdir)
            txt_file_path: Optional[Path] = None

            with zipfile.ZipFile(zip_path, "r") as z:
                for name in z.namelist():
                    if name.lower().endswith(".txt"):
                        z.extract(name, tmp_dir_path)
                        txt_file_path = tmp_dir_path / name
                        break

            if not txt_file_path or not txt_file_path.exists():
                raise FileNotFoundError(f"No se encontró un archivo .txt con balances en el ZIP: {zip_path}")

            con = duckdb.connect()
            con.execute("PRAGMA threads=4;")

            # Transformación canónica garantizada:
            # - Limpieza de comillas
            # - Conversión de fecha a TIMESTAMP_NS
            # - Reemplazo de coma decimal por punto en montos numéricos
            # - Sustitución de nulos o guiones por 0.0
            query = f"""
            COPY (
                SELECT 
                    strptime(replace("FECHA DE CORTE", '"', ''), '%Y-%m-%d')::TIMESTAMP_NS AS fecha_de_corte,
                    replace("SEGMENTO", '"', '') AS segmento,
                    replace("RUC", '"', '') AS ruc,
                    replace("RAZON SOCIAL", '"', '') AS razon_social,
                    replace("CUENTA", '"', '') AS cuenta,
                    replace("DESCRIPCION CUENTA", '"', '') AS descripcion_cuenta,
                    COALESCE(
                        TRY_CAST(REPLACE(REPLACE(REPLACE(replace("SALDO (USD)", '"', ''), ' ', ''), ',', '.'), '-', '0') AS DOUBLE),
                        0.0
                    ) AS saldo__usd_
                FROM read_csv('{txt_file_path.as_posix()}', delim='\\t', header=true, quote='\"', all_varchar=true)
            ) TO '{output_parquet.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);
            """
            con.execute(query)

        # Validación de integridad post-extracción
        con = duckdb.connect()
        row = con.execute(f"""
            SELECT 
                COUNT(*) AS cnt,
                MIN(fecha_de_corte)::VARCHAR AS min_date,
                MAX(fecha_de_corte)::VARCHAR AS max_date
            FROM '{output_parquet.as_posix()}'
        """).fetchone()

        if not row or row[0] == 0:
            raise ValueError(f"Error generando Parquet: {output_parquet} está vacío o corrupto.")

        return {
            "records": row[0],
            "min_date": row[1],
            "max_date": row[2],
            "file_size": output_parquet.stat().st_size,
            "parquet_path": str(output_parquet)
        }

    def process_patrimonio_tecnico(self, zip_path: Path) -> int:
        """
        Copia el ZIP de patrimonio técnico al directorio raw e invoca la extracción analítica.
        """
        from etl.ingest_patrimonio_tecnico import extract_patrimonio_tecnico
        df = extract_patrimonio_tecnico()
        return len(df)

    def sync(
        self,
        force: bool = False,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la sincronización completa:
        1. Descubre descargas disponibles en el portal.
        2. Determina si existen años nuevos o si se fuerza la descarga.
        3. Descarga e ingesta los balances B11 y patrimonio técnico.
        """
        def report(stage: str, percent: int, detail: str = ""):
            if progress_callback:
                progress_callback(stage, percent, detail)

        report("downloading", 10, "Consultando portal web de la SEPS...")
        catalog = self.discover_downloads()
        latest_web_year = catalog["latest_year_available"]

        # Determinar periodos actuales en data/interim
        existing_years = set()
        for p in INTERIM_EEFF_DIR.glob("*.parquet"):
            m = re.search(r'(20\d{2})', p.name)
            if m:
                existing_years.add(int(m.group(1)))

        current_max_year = max(existing_years) if existing_years else 2018

        download_plan_years = []
        for y, d_id in sorted(catalog["eeff_mensuales_bases"].items()):
            if force or y > current_max_year or y == latest_web_year:
                download_plan_years.append((y, d_id))

        if not download_plan_years and not force:
            report("idle", 100, f"El sistema ya cuenta con los datos más recientes ({current_max_year}).")
            return {
                "status": "already_up_to_date",
                "current_year": current_max_year,
                "latest_web_year": latest_web_year,
                "updated_files": []
            }

        updated_files = []
        total_steps = len(download_plan_years) + 1  # balances + patrimonio
        current_step = 0

        # Descarga e ingesta de balances B11
        for year, download_id in download_plan_years:
            current_step += 1
            pct = 10 + int((current_step / total_steps) * 60)
            report("downloading", pct, f"Descargando balances B11 año {year} (ID {download_id})...")

            raw_zip = RAW_EEFF_DIR / f"descarga_{download_id}.zip"
            self.download_file(download_id, raw_zip)

            report("extracting", pct + 5, f"Transformando balances B11 año {year} a Parquet...")
            out_parquet = INTERIM_EEFF_DIR / f"eeff_men_{year}.parquet"
            meta = self.extract_eeff_b11_to_parquet(raw_zip, out_parquet)
            updated_files.append({
                "type": "b11_balances",
                "year": year,
                "download_id": download_id,
                **meta
            })

        # Descarga e ingesta de Patrimonio Técnico
        if latest_web_year in catalog["patrimonio_tecnico"]:
            pat_id = catalog["patrimonio_tecnico"][latest_web_year]
            report("downloading", 80, f"Descargando Patrimonio Técnico año {latest_web_year} (ID {pat_id})...")
            raw_pat_zip = RAW_PAT_DIR / f"descarga_{pat_id}.zip"
            self.download_file(pat_id, raw_pat_zip)

            report("extracting", 90, "Actualizando interim de Patrimonio Técnico (ACPR)...")
            pat_count = self.process_patrimonio_tecnico(raw_pat_zip)
            updated_files.append({
                "type": "patrimonio_tecnico",
                "year": latest_web_year,
                "download_id": pat_id,
                "records": pat_count
            })

        report("success", 100, f"Sincronización web completada. Periodo disponible hasta {latest_web_year}.")
        return {
            "status": "success",
            "latest_web_year": latest_web_year,
            "updated_files": updated_files
        }

seps_crawler = SepsCrawler()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crawler y Extractor SEPS (ESPOCH-DI-060)")
    parser.add_argument("--discover", action="store_true", help="Descubrir descargas disponibles en el portal")
    parser.add_argument("--sync", action="store_true", help="Ejecutar sincronización completa hacia data/interim")
    parser.add_argument("--force", action="store_true", help="Forzar re-descarga de periodos existentes")

    args = parser.parse_args()
    if args.discover:
        print("[*] Consultando portal SEPS...")
        cat = seps_crawler.discover_downloads()
        print(f"Descargas encontradas:")
        print(f"  Último año disponible: {cat['latest_year_available']}")
        print(f"  Bases de balances mensuales: {cat['eeff_mensuales_bases']}")
        print(f"  Patrimonio técnico:          {cat['patrimonio_tecnico']}")
    elif args.sync:
        print(f"[*] Iniciando sincronización web (force={args.force})...")
        def cli_progress(stage, pct, msg):
            print(f"  [{stage.upper():10}] {pct:3}% -> {msg}")
        result = seps_crawler.sync(force=args.force, progress_callback=cli_progress)
        print(f"[+] Resultado: {result['status']}")
    else:
        parser.print_help()
