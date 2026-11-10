import csv
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
import xlsxwriter
import duckdb

from backend.app.core.config import settings
from backend.app.models.schemas import ExportRequest, BenchmarkingCompareRequest
from backend.app.services.benchmarking_service import benchmarking_service
from backend.app.services.camel_evaluator import camel_evaluator

def format_coop_name(full_name: str | None) -> str:
    """Limpia y destaca el nombre comercial distintivo de una cooperativa en reportes CSV y Excel."""
    if not full_name:
        return ""
    name = full_name.strip()
    name = re.sub(
        r"^(COOPERATIVA DE AHORRO Y CR[EÉ]DITO|MUTUALISTA DE AHORRO Y CR[EÉ]DITO PARA LA VIVIENDA|MUTUALISTA|CAJA CENTRAL|COOPERATIVA)\s+",
        "",
        name,
        flags=re.IGNORECASE
    )
    name = re.sub(r"\s+(LIMITADA|LTDA\.?|S\.A\.?)$", "", name, flags=re.IGNORECASE).strip()
    if not name:
        return full_name

    # Title Case respetando siglas y palabras comunes
    acronyms = {"JEP", "CREA", "OSCUS", "CACPE", "COOPMEGO", "FINANCOOP", "FEDECACES"}
    small_words = {"de", "del", "la", "las", "el", "los", "y", "en"}
    words = name.lower().split()
    formatted_words = []
    for idx, w in enumerate(words):
        upper = w.upper()
        if upper in acronyms:
            formatted_words.append(upper)
        elif idx > 0 and w in small_words:
            formatted_words.append(w)
        else:
            formatted_words.append(w.capitalize())
    return " ".join(formatted_words)

class ExportService:
    """Pipeline de exportación y streaming de microdatos y reportes multi-pestaña para la Capa Pro."""

    def __init__(self, mart_dir: Path | None = None):
        self.mart_dir = mart_dir or settings.DATA_MART_DIR
        self._con = duckdb.connect()
        self._con.execute("PRAGMA threads=4;")

    def _p(self, name: str) -> str:
        return str(self.mart_dir / f"{name}.parquet").replace("\\", "/")

    def _p_entity_partitioned(self) -> str:
        """Ruta al árbol de particiones Hive en Parquet para optimizar consultas de microdatos con partition pruning."""
        partitioned_path = self.mart_dir / "partitioned" / "fct_indicators_entity"
        if partitioned_path.exists():
            return str(partitioned_path / "*/*/*.parquet").replace("\\", "/")
        return self._p("fct_indicators_entity_monthly")

    def stream_csv(self, req: ExportRequest, delimiter: str = ",") -> Generator[str, None, None]:
        """Genera y emite en streaming el archivo CSV con los microdatos granulares de las cooperativas."""
        cursor = self._con.cursor()
        try:
            ruc_in_clause = ",".join([f"'{ruc}'" for ruc in req.entity_ids])

            # Emitir UTF-8 BOM para apertura nativa e inmediata en Excel en español
            yield "\ufeff"

            # Cabecera CSV
            headers = [
                "periodo",
                "ruc",
                "nombre_comercial",
                "razon_social",
                "segmento",
                "provincia",
                "indicador_id",
                "indicador_nombre",
                "dimension_camel",
                "valor_porcentaje",
                "linea_base_segmento1",
                "media_nacional",
                "semaforo_estado",
                "normativa_referencia",
                "evaluacion_mensaje"
            ]
            header_sio = io.StringIO()
            csv.writer(header_sio, delimiter=delimiter).writerow(headers)
            yield header_sio.getvalue()

            # Consultar microdatos combinando dimensiones y líneas base en DuckDB aprovechando particionado Hive
            query = f"""
                SELECT 
                    e.period,
                    e.ruc,
                    COALESCE(dim.razon_social, e.ruc) AS razon_social,
                    COALESCE(dim.segment, 'SEGMENTO_1') AS segmento,
                    COALESCE(dim.province_name, 'NACIONAL') AS provincia,
                    e.indicator_id,
                    e.value AS entidad_valor,
                    seg.value AS seg1_valor,
                    cty.value AS cty_valor
                FROM read_parquet('{self._p_entity_partitioned()}', hive_partitioning=true) e
                LEFT JOIN read_parquet('{self._p("dim_entities")}') dim 
                       ON e.ruc = dim.ruc
                LEFT JOIN read_parquet('{self._p("fct_indicators_segment_monthly")}') seg
                       ON e.indicator_id = seg.indicator_id 
                      AND e.period = seg.period 
                      AND seg.segment = 'SEGMENTO_1'
                LEFT JOIN read_parquet('{self._p("fct_indicators_country_monthly")}') cty
                       ON e.indicator_id = cty.indicator_id 
                      AND e.period = cty.period
                WHERE e.ruc IN ({ruc_in_clause})
                  AND e.period >= ? AND e.period <= ?
                ORDER BY e.period ASC, e.indicator_id ASC, e.ruc ASC;
            """

            cursor.execute(query, [req.start_date, req.end_date])
            spec_map = {i["id"]: i for i in benchmarking_service.spec.get("indicators", [])}

            batch_size = 500
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                batch_sio = io.StringIO()
                writer = csv.writer(batch_sio, delimiter=delimiter)

                for r in rows:
                    period, ruc, razon_social, segmento, provincia, ind_id, val, seg_val, cty_val = r
                    ind_spec = spec_map.get(ind_id, {})
                    dim = ind_spec.get("category", "calidad_de_activos")
                    
                    if req.camel_dimension and dim != req.camel_dimension:
                        continue

                    ind_name = ind_spec.get("name", ind_id)
                    polarity = ind_spec.get("polarity", "higher_is_better")

                    eval_res = camel_evaluator.evaluate(
                        indicator_id=ind_id,
                        value=float(val) if val is not None else None,
                        default_polarity=polarity,
                        indicator_name=ind_name
                    )

                    clean_coop = format_coop_name(razon_social)
                    writer.writerow([
                        period,
                        ruc,
                        clean_coop,
                        razon_social,
                        segmento,
                        provincia,
                        ind_id,
                        ind_name,
                        dim,
                        f"{float(val):.4f}" if val is not None else "",
                        f"{float(seg_val):.4f}" if seg_val is not None else "",
                        f"{float(cty_val):.4f}" if cty_val is not None else "",
                        eval_res.status,
                        eval_res.normative_reference,
                        eval_res.message
                    ])

                chunk = batch_sio.getvalue()
                if chunk:
                    yield chunk

        finally:
            cursor.close()

    def generate_excel(self, req: ExportRequest) -> bytes:
        """Genera un libro Excel multi-pestaña profesional para Unidades de Riesgo y Auditoría."""
        compare_req = BenchmarkingCompareRequest(
            entity_ids=req.entity_ids,
            start_date=req.start_date,
            end_date=req.end_date,
            camel_dimension=req.camel_dimension
        )
        compare_res = benchmarking_service.compare(compare_req)

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True, "constant_memory": True})

        # Estilos y Paleta Institucional Fintech Esmeralda (ESPOCH)
        title_fmt = wb.add_format({
            "bold": True,
            "font_size": 13,
            "font_color": "#064E3B",
            "bottom": 2,
            "bottom_color": "#047857"
        })
        subtitle_fmt = wb.add_format({"font_size": 9, "italic": True, "font_color": "#374151"})
        header_fmt = wb.add_format({
            "bold": True,
            "bg_color": "#064E3B",
            "font_color": "#FFFFFF",
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#047857",
            "text_wrap": True,
            "font_size": 10
        })
        cell_fmt = wb.add_format({"border": 1, "border_color": "#E5E7EB", "valign": "vcenter", "font_size": 9})
        num_fmt = wb.add_format({"border": 1, "border_color": "#E5E7EB", "num_format": "0.00%", "align": "right", "valign": "vcenter", "font_size": 9})
        num_dec_fmt = wb.add_format({"border": 1, "border_color": "#E5E7EB", "num_format": "0.00", "align": "right", "valign": "vcenter", "font_size": 9})

        # Semáforos Institucionales (Sobrios y Claros)
        green_fmt = wb.add_format({
            "bg_color": "#D1FAE5",
            "font_color": "#065F46",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#A7F3D0",
            "font_size": 9
        })
        yellow_fmt = wb.add_format({
            "bg_color": "#FEF3C7",
            "font_color": "#92400E",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#FDE68A",
            "font_size": 9
        })
        red_fmt = wb.add_format({
            "bg_color": "#FEE2E2",
            "font_color": "#991B1B",
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#FECACA",
            "font_size": 9
        })

        # ==============================================================
        # Hoja 1: Resumen Benchmarking con Semáforos
        # ==============================================================
        ws1 = wb.add_worksheet("Resumen Benchmarking")
        ws1.set_tab_color("#047857")
        ws1.freeze_panes(5, 3)

        # Encabezado Institucional
        ws1.write(0, 0, "ESPOCH – DI – 060: Sistema de Indicadores Financieros SFPS (Capa Pro)", title_fmt)
        ws1.write(1, 0, f"Reporte de Benchmarking Multi-Entidad con Semáforo Normativo SEPS / COMF | Ventana: {req.start_date} a {req.end_date}", subtitle_fmt)
        ws1.write(2, 0, f"Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Entidades analizadas: {len(compare_res.entities)}", subtitle_fmt)

        headers_ws1 = ["Ficha SEPS", "Indicador Financiero", "Dimensión CAMEL", "Segmento 1 (Base)", "Nacional (Media)"]
        for ent in compare_res.entities:
            clean_name = format_coop_name(ent.razon_social)
            headers_ws1.append(f"{clean_name} (Valor)")
            headers_ws1.append(f"{clean_name} (Semáforo)")

        ws1.set_row(4, 28)
        for col_idx, h in enumerate(headers_ws1):
            ws1.write(4, col_idx, h, header_fmt)

        ws1.set_column(0, 0, 10)
        ws1.set_column(1, 1, 38)
        ws1.set_column(2, 2, 22)
        ws1.set_column(3, 4, 18)
        for i in range(len(compare_res.entities)):
            ws1.set_column(5 + (i * 2), 5 + (i * 2), 18)
            ws1.set_column(6 + (i * 2), 6 + (i * 2), 16)

        row_cursor = 5
        for ind in compare_res.indicators:
            ws1.write(row_cursor, 0, ind.seps_ficha_number or "-", cell_fmt)
            ws1.write(row_cursor, 1, ind.indicator_name, cell_fmt)
            ws1.write(row_cursor, 2, ind.dimension.replace("_", " ").title(), cell_fmt)
            
            # Líneas base
            fmt_to_use = num_fmt if ind.unit == "percent" else num_dec_fmt
            ws1.write(row_cursor, 3, (ind.segment1_baseline / 100.0) if (ind.segment1_baseline is not None and ind.unit == "percent") else ind.segment1_baseline, fmt_to_use)
            ws1.write(row_cursor, 4, (ind.country_baseline / 100.0) if (ind.country_baseline is not None and ind.unit == "percent") else ind.country_baseline, fmt_to_use)

            col_cursor = 5
            for ent in compare_res.entities:
                val = ind.entity_values.get(ent.ruc)
                ev = ind.entity_evaluations.get(ent.ruc)
                status = ev.status if ev else "YELLOW"

                calc_val = (val / 100.0) if (val is not None and ind.unit == "percent") else val
                ws1.write(row_cursor, col_cursor, calc_val if calc_val is not None else "N/D", fmt_to_use)

                status_fmt = green_fmt if status == "GREEN" else (yellow_fmt if status == "YELLOW" else red_fmt)
                label_status = "CUMPLE (VERDE)" if status == "GREEN" else ("ALERTA (AMARILLO)" if status == "YELLOW" else "CRÍTICO (ROJO)")
                ws1.write(row_cursor, col_cursor + 1, label_status, status_fmt)
                col_cursor += 2

            row_cursor += 1

        # ==============================================================
        # Hoja 2: Series Históricas
        # ==============================================================
        ws2 = wb.add_worksheet("Series Históricas")
        ws2.set_tab_color("#059669")
        ws2.freeze_panes(1, 4)

        headers_ws2 = ["Periodo", "Indicador ID", "Indicador Nombre", "Dimensión CAMEL", "Segmento 1 Base", "Media Nacional"]
        for ent in compare_res.entities:
            clean_name = format_coop_name(ent.razon_social)
            headers_ws2.append(f"{clean_name} ({ent.ruc[:10]})")

        ws2.set_row(0, 24)
        for c_idx, h in enumerate(headers_ws2):
            ws2.write(0, c_idx, h, header_fmt)

        ws2.set_column(0, 0, 12)
        ws2.set_column(1, 1, 28)
        ws2.set_column(2, 2, 38)
        ws2.set_column(3, 3, 20)
        ws2.set_column(4, 5, 18)
        for i in range(len(compare_res.entities)):
            ws2.set_column(6 + i, 6 + i, 22)

        row_ws2 = 1
        for ind in compare_res.indicators:
            pts = compare_res.time_series.get(ind.indicator_id, [])
            for pt in pts:
                ws2.write(row_ws2, 0, pt.period, cell_fmt)
                ws2.write(row_ws2, 1, ind.indicator_id, cell_fmt)
                ws2.write(row_ws2, 2, ind.indicator_name, cell_fmt)
                ws2.write(row_ws2, 3, ind.dimension.replace("_", " ").title(), cell_fmt)

                s1_val = (pt.segment1_baseline / 100.0) if (pt.segment1_baseline is not None and ind.unit == "percent") else pt.segment1_baseline
                cty_val = (pt.country_baseline / 100.0) if (pt.country_baseline is not None and ind.unit == "percent") else pt.country_baseline
                ws2.write(row_ws2, 4, s1_val if s1_val is not None else "", num_fmt if ind.unit == "percent" else num_dec_fmt)
                ws2.write(row_ws2, 5, cty_val if cty_val is not None else "", num_fmt if ind.unit == "percent" else num_dec_fmt)

                for e_idx, ent in enumerate(compare_res.entities):
                    e_val = pt.entity_values.get(ent.ruc)
                    calc_e_val = (e_val / 100.0) if (e_val is not None and ind.unit == "percent") else e_val
                    ws2.write(row_ws2, 6 + e_idx, calc_e_val if calc_e_val is not None else "", num_fmt if ind.unit == "percent" else num_dec_fmt)

                row_ws2 += 1

        # ==============================================================
        # Hoja 3: Ficha Metodológica SEPS
        # ==============================================================
        ws3 = wb.add_worksheet("Ficha Metodológica SEPS")
        ws3.set_tab_color("#10B981")
        ws3.freeze_panes(1, 2)

        headers_ws3 = [
            "Ficha SEPS", "ID Indicador", "Nombre Metodológico", "Dimensión CAMEL",
            "Polaridad", "Unidad", "Fórmula Contable B11", "Umbral Normativo", "Descripción Técnica"
        ]
        ws3.set_row(0, 24)
        for c_idx, h in enumerate(headers_ws3):
            ws3.write(0, c_idx, h, header_fmt)

        ws3.set_column(0, 0, 12)
        ws3.set_column(1, 1, 28)
        ws3.set_column(2, 2, 40)
        ws3.set_column(3, 4, 18)
        ws3.set_column(5, 5, 12)
        ws3.set_column(6, 6, 45)
        ws3.set_column(7, 7, 30)
        ws3.set_column(8, 8, 55)

        row_ws3 = 1
        for ind_meta in benchmarking_service.spec.get("indicators", []):
            ind_id = ind_meta["id"]
            threshold_info = camel_evaluator._config.get("indicators", {}).get(ind_id, {})
            norm_ref = threshold_info.get("normative_reference", "Normativa SEPS v3.0")

            ws3.write(row_ws3, 0, ind_meta.get("seps_ficha_number") or "-", cell_fmt)
            ws3.write(row_ws3, 1, ind_id, cell_fmt)
            ws3.write(row_ws3, 2, ind_meta.get("name", ind_id), cell_fmt)
            ws3.write(row_ws3, 3, ind_meta.get("category", "").replace("_", " ").title(), cell_fmt)
            ws3.write(row_ws3, 4, ind_meta.get("polarity", ""), cell_fmt)
            ws3.write(row_ws3, 5, ind_meta.get("unit", ""), cell_fmt)
            ws3.write(row_ws3, 6, ind_meta.get("formula", ""), cell_fmt)
            ws3.write(row_ws3, 7, norm_ref, cell_fmt)
            ws3.write(row_ws3, 8, ind_meta.get("description", ""), cell_fmt)
            row_ws3 += 1

        wb.close()
        output.seek(0)
        return output.getvalue()

# Singleton del servicio de exportación
export_service = ExportService()
