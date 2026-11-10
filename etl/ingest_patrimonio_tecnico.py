"""
ETL Ingestión: Reportes de Patrimonio Técnico (ACPR / Ficha 62)
Procesa los boletines mensuales de Patrimonio Técnico de la SEPS (2018 - 2025).
Extrae:
- Ficha 58: Patrimonio Técnico Primario (PTP)
- Ficha 59: Patrimonio Técnico Secundario (PTS)
- Ficha 60: Patrimonio Técnico Constituido (PTC)
- Ficha 61: Activos y Contingentes Ponderados por Riesgo (APR)
- Ficha 62: Solvencia Legal ACPR (PTC / APR * 100)
"""

import zipfile
import glob
import io
import re
import os
from pathlib import Path
import duckdb
import openpyxl
import polars as pl

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "Situación Financiera" / "Reportes" / "Patrimonio técnico"
INTERIM_DIR = BASE_DIR / "data" / "interim" / "patrimonio_tecnico"
MART_DIR = BASE_DIR / "data" / "processed" / "mart"

MONTH_MAP = {
    'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04', 'MAY': '05', 'JUN': '06',
    'JUL': '07', 'AGO': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12',
    'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04', 'MAYO': '05',
    'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08', 'SEPTIEMBRE': '09', 'OCTUBRE': '10',
    'NOVIEMBRE': '11', 'DICIEMBRE': '12'
}

def to_float(val) -> float | None:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip().replace(" ", "").replace(",", "")
    try:
        return float(val_str)
    except ValueError:
        return None

def parse_period(sheet_name: str) -> str | None:
    # Ej: 'ENE_2022', '3.12.DIC_2025', '4.2 DIC_2024', 'Diciembre_2019 '
    m = re.search(r'(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC|ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)[\w\s\.]*(\d{4})', sheet_name, re.IGNORECASE)
    if not m:
        m = re.search(r'(\d{4})[\w\s\.]*(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC|ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)', sheet_name, re.IGNORECASE)
        if m:
            year = m.group(1)
            month = MONTH_MAP.get(m.group(2).upper()[:3], '01')
            return f"{year}-{month}"
        return None
    month = MONTH_MAP.get(m.group(1).upper()[:3], '01')
    year = m.group(2)
    return f"{year}-{month}"

def extract_patrimonio_tecnico() -> pl.DataFrame:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    zip_paths = sorted(glob.glob(str(RAW_DIR / "*.zip")))
    print(f"[Patrimonio Técnico] Encontrados {len(zip_paths)} archivos ZIP en raw.")

    rows = []
    # Usar dim_entities para validar y mapear segmento / provincia
    con = duckdb.connect()
    entities_path = str(MART_DIR / "dim_entities.parquet").replace("\\", "/")
    dim_entities = con.execute(f"SELECT ruc, segment, province_code FROM read_parquet('{entities_path}')").fetchall()
    entity_meta = {r[0]: {"segment": r[1], "province_code": r[2]} for r in dim_entities}

    for zpath in zip_paths:
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():
                if name.startswith("__MACOSX") or not name.endswith((".xlsx", ".xlsm")):
                    continue
                
                try:
                    data = z.read(name)
                    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
                    for sname in wb.sheetnames:
                        period = parse_period(sname)
                        if not period or period < "2018-01":
                            continue
                        
                        sheet = wb[sname]
                        # Buscar fila encabezado con 'RUC'
                        header_row = None
                        ruc_col = None
                        for r_idx in range(1, 25):
                            cell_values = [str(c.value).strip().upper() if c.value is not None else '' for c in sheet[r_idx]]
                            if 'RUC' in cell_values:
                                header_row = r_idx
                                ruc_col = cell_values.index('RUC') + 1
                                break
                        
                        if not header_row or not ruc_col:
                            continue
                        
                        # Extraer entidades
                        for r_idx in range(header_row + 1, sheet.max_row + 1):
                            ruc_cell = sheet.cell(row=r_idx, column=ruc_col).value
                            if ruc_cell is None:
                                continue
                            
                            ruc_str = re.sub(r'\D', '', str(ruc_cell).strip())
                            if len(ruc_str) == 12:
                                ruc_str = '0' + ruc_str
                            if len(ruc_str) != 13:
                                continue
                            
                            ptp = to_float(sheet.cell(row=r_idx, column=ruc_col + 2).value)
                            pts = to_float(sheet.cell(row=r_idx, column=ruc_col + 3).value)
                            ptc = to_float(sheet.cell(row=r_idx, column=ruc_col + 4).value)
                            apr = to_float(sheet.cell(row=r_idx, column=ruc_col + 5).value)
                            solvencia_raw = to_float(sheet.cell(row=r_idx, column=ruc_col + 6).value)

                            # Recalcular solvencia de forma exacta
                            if ptc is not None and apr is not None and apr > 0:
                                solvencia = round((ptc / apr) * 100, 4)
                            elif solvencia_raw is not None:
                                solvencia = round(solvencia_raw * 100 if solvencia_raw <= 1.0 else solvencia_raw, 4)
                            else:
                                solvencia = None

                            ent_info = entity_meta.get(ruc_str, {"segment": "SEGMENTO_1", "province_code": "01"})

                            rows.append({
                                "period": period,
                                "ruc": ruc_str,
                                "segment": ent_info["segment"],
                                "province_code": ent_info["province_code"],
                                "ptp": ptp,
                                "pts": pts,
                                "ptc": ptc,
                                "apr": apr,
                                "solvencia": solvencia
                            })
                except Exception as e:
                    print(f"Advertencia al leer {name} en {os.path.basename(zpath)}: {e}")

    df = pl.DataFrame(rows).unique(subset=["period", "ruc"])
    out_path = INTERIM_DIR / "patrimonio_tecnico_monthly.parquet"
    df.write_parquet(out_path)
    print(f"[Patrimonio Técnico] {len(df)} registros procesados guardados en {out_path}.")
    return df

if __name__ == "__main__":
    extract_patrimonio_tecnico()
