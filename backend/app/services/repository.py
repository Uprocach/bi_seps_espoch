import json
import duckdb
from contextlib import contextmanager
from typing import List, Optional, Generator, Any
from datetime import datetime, timezone
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.errors import APIProblemException
from backend.app.services.mart_provider import mart_provider, MartPathProvider
from backend.app.models.schemas import (
    BenchmarkingCompareRequest,
    BenchmarkingCompareResponse,
    BenchmarkingIndicatorRow,
    BenchmarkingSeriesPoint,
    BenchmarkingRankingResponse,
    EntityRankingItem,
    IndicatorMeta,
    EntitySummary,
    Province,
    Polarity
)
from backend.app.services.camel_evaluator import camel_evaluator
from backend.app.services.export_formatter import format_coop_name

class AnalyticsRepository:
    ALLOWED_SORT_FIELDS = {
        "total_assets_usd": "total_assets_usd",
        "razon_social": "razon_social",
        "ruc": "ruc",
        "first_period": "first_period",
        "last_period": "last_period"
    }

    def __init__(self, mart_dir: Path | None = None):
        self.mart_provider = MartPathProvider(mart_dir) if mart_dir else mart_provider
        self.mart_dir = self.mart_provider.mart_dir
        self.spec = self._load_spec()
        self._con = self.mart_provider.create_connection(threads=4)

    @contextmanager
    def get_cursor(self):
        """Provee un cursor thread-safe dedicado por cada solicitud HTTP."""
        cursor = self._con.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def _load_spec(self) -> dict:
        with open(settings.INDICATORS_SPEC_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _p(self, name: str) -> str:
        return self.mart_provider.p(name)

    def _p_entity_partitioned(self) -> str:
        """Ruta al árbol de particiones Hive en Parquet para optimizar consultas de microdatos con partition pruning."""
        return self.mart_provider.p_entity_partitioned()

    def get_metadata_filters(self) -> dict:
        with self.get_cursor() as cursor:
            # Segmentos con conteo de entidades activas
            seg_rows = cursor.execute(f"""
                SELECT s.code, s.label, s.reporting_frequency, 
                       COUNT(e.ruc) AS entity_count
                FROM read_parquet('{self._p("dim_segments")}') s
                LEFT JOIN read_parquet('{self._p("dim_entities")}') e 
                       ON s.code = e.segment AND e.is_active = TRUE
                GROUP BY s.code, s.label, s.reporting_frequency
                ORDER BY s.code;
            """).fetchall()

            segments = [
                {"code": r[0], "label": r[1], "reporting_frequency": r[2], "entity_count": r[3]}
                for r in seg_rows
            ]

            # Provincias con conteo de entidades
            prov_rows = cursor.execute(f"""
                SELECT p.code, p.name, COUNT(e.ruc) AS entity_count
                FROM read_parquet('{self._p("dim_provinces")}') p
                LEFT JOIN read_parquet('{self._p("dim_entities")}') e ON p.code = e.province_code
                GROUP BY p.code, p.name
                ORDER BY p.code;
            """).fetchall()

            provinces = [
                {"code": r[0], "name": r[1], "entity_count": r[2]}
                for r in prov_rows
            ]

            # Catálogo de periodos
            per_rows = cursor.execute(f"""
                SELECT DISTINCT period
                FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                ORDER BY period;
            """).fetchall()

            available_periods = [r[0] for r in per_rows]
            min_p = available_periods[0] if available_periods else "2018-01"
            max_p = available_periods[-1] if available_periods else "2025-12"

            periods = {
                "frequency": "monthly",
                "min": min_p,
                "max": max_p,
                "latest": max_p,
                "available": available_periods
            }

            # Catálogo de indicadores y últimos valores nacionales
            self.spec = self._load_spec()
            latest_vals = {}
            if max_p:
                try:
                    lv_rows = cursor.execute(f"""
                        SELECT indicator_id, value 
                        FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                        WHERE period = ?;
                    """, [max_p]).fetchall()
                    latest_vals = {r[0]: float(r[1]) if r[1] is not None else None for r in lv_rows}
                except Exception:
                    latest_vals = {}

            indicators = []
            for ind in self.spec.get("indicators", []):
                if ind.get("status") != "pending_source":
                    indicators.append({
                        "id": ind["id"],
                        "name": ind["name"],
                        "short_name": ind.get("short_name", ind["name"]),
                        "category": ind["category"],
                        "unit": ind["unit"],
                        "decimals": ind["decimals"],
                        "polarity": ind["polarity"],
                        "seps_ficha_number": ind.get("seps_ficha_number"),
                        "latest_value": latest_vals.get(ind["id"]),
                        "methodological_note": ind.get("methodological_note")
                    })

            return {
                "segments": segments,
                "provinces": provinces,
                "periods": periods,
                "indicators": indicators,
                "data_as_of": f"{max_p}-31"
            }

    def list_entities(
        self,
        segment: Optional[List[str]] = None,
        province: Optional[List[str]] = None,
        q: Optional[str] = None,
        active: Optional[bool] = None,
        sort: str = "-total_assets_usd",
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        direction = "DESC" if sort.startswith("-") else "ASC"
        clean_sort = sort.lstrip("-")

        # Validación estricta contra lista blanca (Mitigación AUD-01)
        if clean_sort not in self.ALLOWED_SORT_FIELDS:
            raise APIProblemException(
                status_code=400,
                title="Parámetro inválido",
                detail=f"El campo de ordenamiento '{clean_sort}' no está permitido."
            )

        sort_column = self.ALLOWED_SORT_FIELDS[clean_sort]
        where_clauses = []
        params = []

        if segment:
            placeholders = ", ".join(["?"] * len(segment))
            where_clauses.append(f"segment IN ({placeholders})")
            params.extend(segment)
        if province:
            placeholders = ", ".join(["?"] * len(province))
            where_clauses.append(f"province_code IN ({placeholders})")
            params.extend(province)
        if q:
            where_clauses.append("(UPPER(razon_social) LIKE ? OR ruc LIKE ?)")
            wildcard_q = f"%{q.strip().upper()}%"
            params.extend([wildcard_q, wildcard_q])
        if active is True:
            where_clauses.append("is_active = TRUE")
        elif active is False:
            where_clauses.append("is_active = FALSE")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        order_sql = f"ORDER BY {sort_column} {direction} NULLS LAST"

        with self.get_cursor() as cursor:
            count_sql = f"SELECT COUNT(*) FROM read_parquet('{self._p('dim_entities')}') {where_sql};"
            total_items = cursor.execute(count_sql, params).fetchone()[0]
            total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT ruc, razon_social, entity_type, segment, province_code, province_name,
                       total_assets_usd, first_period, last_period, is_active
                FROM read_parquet('{self._p('dim_entities')}')
                {where_sql}
                {order_sql}
                LIMIT ? OFFSET ?;
            """
            rows = cursor.execute(query_sql, params + [page_size, offset]).fetchall()

        return {
            "data": [
                {
                    "ruc": r[0], "razon_social": r[1], "entity_type": r[2], "segment": r[3],
                    "province": {"code": r[4], "name": r[5]} if r[4] else None,
                    "total_assets_usd": float(r[6]) if r[6] is not None else None,
                    "first_period": r[7], "last_period": r[8], "is_active": bool(r[9])
                } for r in rows
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages
            }
        }

    def get_indicator_series(
        self,
        indicator: str,
        level: str,
        segment: list[str] | None = None,
        province: list[str] | None = None,
        ruc: list[str] | None = None,
        from_period: str | None = None,
        to_period: str | None = None
    ) -> dict:
        with self.get_cursor() as cursor:
            # Validar indicador
            self.spec = self._load_spec()
            ind_meta = next((i for i in self.spec.get("indicators", []) if i["id"] == indicator), None)
            if not ind_meta:
                raise APIProblemException(
                    status_code=400,
                    title="Indicador no encontrado",
                    detail=f"El indicador '{indicator}' no existe en el catálogo."
                )

            # Rango por defecto: últimos 12 periodos si se omite
            if not to_period:
                to_period = cursor.execute(f"SELECT MAX(period) FROM read_parquet('{self._p('fct_indicators_country_monthly')}');").fetchone()[0]
            if not from_period:
                # Calcular 11 meses atrás
                y, m = int(to_period[:4]), int(to_period[5:])
                m_start = m - 11
                y_start = y
                while m_start <= 0:
                    m_start += 12
                    y_start -= 1
                from_period = f"{y_start:04d}-{m_start:02d}"

            if from_period > to_period:
                raise APIProblemException(
                    status_code=422,
                    title="Rango de fechas inválido",
                    detail=f"El periodo inicial 'from' ({from_period}) no puede ser mayor que 'to' ({to_period})."
                )

            series_list = []

            if level == "country":
                # Nivel País
                rows = cursor.execute(f"""
                    SELECT period, value, numerator, denominator, entity_count
                    FROM read_parquet('{self._p('fct_indicators_country_monthly')}')
                    WHERE indicator_id = ? AND period >= ? AND period <= ?
                    ORDER BY period;
                """, [indicator, from_period, to_period]).fetchall()

                points = [
                    {
                        "period": r[0],
                        "value": float(r[1]) if r[1] is not None else None,
                        "numerator": float(r[2]) if r[2] is not None else None,
                        "denominator": float(r[3]) if r[3] is not None else None,
                        "entity_count": int(r[4])
                    }
                    for r in rows
                ]
                series_list.append({
                    "key": "EC",
                    "label": "Sistema SFPS (Segmentos 1-3 y Mutualistas)",
                    "level": "country",
                    "points": points
                })

            elif level == "segment":
                # Nivel Segmento
                seg_filter_sql = ""
                seg_params = [indicator, from_period, to_period]
                if segment:
                    # Normalizar si el usuario pasa "1" -> "SEGMENTO_1"
                    segment = [f"SEGMENTO_{s}" if s.isdigit() else s for s in segment]
                    placeholders = ", ".join(["?"] * len(segment))
                    seg_filter_sql = f"AND segment IN ({placeholders})"
                    seg_params.extend(segment)

                seg_codes = cursor.execute(f"""
                    SELECT DISTINCT segment
                    FROM read_parquet('{self._p('fct_indicators_segment_monthly')}')
                    WHERE indicator_id = ? AND period >= ? AND period <= ? {seg_filter_sql}
                    ORDER BY segment;
                """, seg_params).fetchall()

                for sc_row in seg_codes:
                    sc = sc_row[0]
                    rows = cursor.execute(f"""
                        SELECT period, value, numerator, denominator, entity_count
                        FROM read_parquet('{self._p('fct_indicators_segment_monthly')}')
                        WHERE indicator_id = ? AND segment = ? AND period >= ? AND period <= ?
                        ORDER BY period;
                    """, [indicator, sc, from_period, to_period]).fetchall()

                    points = [
                        {
                            "period": r[0],
                            "value": float(r[1]) if r[1] is not None else None,
                            "numerator": float(r[2]) if r[2] is not None else None,
                            "denominator": float(r[3]) if r[3] is not None else None,
                            "entity_count": int(r[4])
                        }
                        for r in rows
                    ]
                    # Label amigable
                    label = sc.replace("_", " ").title()
                    series_list.append({
                        "key": sc,
                        "label": label,
                        "level": "segment",
                        "segment": sc,
                        "points": points
                    })

            elif level == "entity":
                if not ruc:
                    raise APIProblemException(
                        status_code=422,
                        title="Error de validación",
                        detail="El parámetro 'ruc' es obligatorio cuando level=entity.",
                        errors=[{"field": "ruc", "message": "required when level=entity"}]
                    )

                for ruc_val in ruc:
                    # Obtener razón social y segmento de la entidad
                    ent_info = cursor.execute(f"""
                        SELECT razon_social, segment
                        FROM read_parquet('{self._p('dim_entities')}')
                        WHERE ruc = ?;
                    """, [ruc_val]).fetchone()

                    if not ent_info:
                        raise APIProblemException(
                            status_code=404,
                            title="Recurso no encontrado",
                            detail=f"No existen datos para el RUC {ruc_val} en el sistema."
                        )

                    rows = cursor.execute(f"""
                        SELECT period, value, numerator, denominator, entity_count
                        FROM read_parquet('{self._p_entity_partitioned()}', hive_partitioning=true)
                        WHERE indicator_id = ? AND ruc = ? AND period >= ? AND period <= ?
                        ORDER BY period;
                    """, [indicator, ruc_val, from_period, to_period]).fetchall()

                    points = [
                        {
                            "period": r[0],
                            "value": float(r[1]) if r[1] is not None else None,
                            "numerator": float(r[2]) if r[2] is not None else None,
                            "denominator": float(r[3]) if r[3] is not None else None,
                            "entity_count": 1
                        }
                        for r in rows
                    ]

                    series_list.append({
                        "key": ruc_val,
                        "label": ent_info[0],
                        "level": "entity",
                        "segment": ent_info[1],
                        "points": points
                    })

            return {
                "indicator": {
                    "id": ind_meta["id"],
                    "name": ind_meta["name"],
                    "short_name": ind_meta.get("short_name", ind_meta["name"]),
                    "category": ind_meta["category"],
                    "unit": ind_meta["unit"],
                    "decimals": ind_meta["decimals"],
                    "polarity": ind_meta["polarity"],
                    "seps_ficha_number": ind_meta.get("seps_ficha_number"),
                    "methodological_note": ind_meta.get("methodological_note")
                },
                "level": level,
                "frequency": "monthly",
                "period_range": {
                    "from": from_period,
                    "to": to_period
                },
                "filters_applied": {
                    "segment": segment or [],
                    "province": province or [],
                    "ruc": ruc or []
                },
                "series": series_list,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

    def get_benchmark_matrix(self, rucs: list[str], period: str | None = None) -> dict:
        """Endpoint consolidado que retorna en una única consulta DuckDB la matriz de benchmarking."""
        with self.get_cursor() as cursor:
            if not period:
                period = cursor.execute(f"SELECT MAX(period) FROM read_parquet('{self._p('fct_indicators_country_monthly')}');").fetchone()[0]

            self.spec = self._load_spec()
            active_indicators = [
                i for i in self.spec.get("indicators", [])
                if i.get("status") != "pending_source"
            ]

            # 1. Valores País para el periodo
            cty_rows = cursor.execute(f"""
                SELECT indicator_id, value
                FROM read_parquet('{self._p('fct_indicators_country_monthly')}')
                WHERE period = ?;
            """, [period]).fetchall()
            cty_map = {r[0]: float(r[1]) if r[1] is not None else None for r in cty_rows}

            # 2. Valores Segmento 1 para el periodo
            seg_rows = cursor.execute(f"""
                SELECT indicator_id, value
                FROM read_parquet('{self._p('fct_indicators_segment_monthly')}')
                WHERE segment = 'SEGMENTO_1' AND period = ?;
            """, [period]).fetchall()
            seg_map = {r[0]: float(r[1]) if r[1] is not None else None for r in seg_rows}

            # 3. Valores Entidad para los RUCs solicitados
            ent_map: dict[str, dict[str, float | None]] = {r: {} for r in rucs}
            if rucs:
                placeholders = ", ".join(["?"] * len(rucs))
                ent_rows = cursor.execute(f"""
                    SELECT ruc, indicator_id, value
                    FROM read_parquet('{self._p_entity_partitioned()}', hive_partitioning=true)
                    WHERE ruc IN ({placeholders}) AND period = ?;
                """, rucs + [period]).fetchall()
                for r_ruc, ind_id, val in ent_rows:
                    ent_map[r_ruc][ind_id] = float(val) if val is not None else None

            # Construir filas de la matriz
            rows = []
            for ind in active_indicators:
                rows.append({
                    "indicator_id": ind["id"],
                    "indicator_name": ind["name"],
                    "category": ind["category"],
                    "unit": ind["unit"],
                    "polarity": ind["polarity"],
                    "methodological_note": ind.get("methodological_note"),
                    "entity_values": {r: ent_map[r].get(ind["id"]) for r in rucs},
                    "segment1_avg": seg_map.get(ind["id"]),
                    "country_avg": cty_map.get(ind["id"])
                })

            return {
                "period": period,
                "rucs": rucs,
                "matrix": rows,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

    def compare_entities(self, req: BenchmarkingCompareRequest) -> BenchmarkingCompareResponse:
        """Contrasta hasta 5 cooperativas simultáneamente contra las líneas base del Segmento 1 y la media nacional."""
        entity_ids = req.entity_ids
        start_date = req.start_date
        end_date = req.end_date
        camel_dimension = req.camel_dimension

        all_indicators = self.spec.get("indicators", [])
        if camel_dimension:
            target_indicators = [
                i for i in all_indicators
                if i.get("category") == camel_dimension and i.get("status") != "pending_source"
            ]
        else:
            target_indicators = [
                i for i in all_indicators
                if i.get("status") != "pending_source"
            ]

        target_ids = {i["id"] for i in target_indicators}

        with self.get_cursor() as cursor:
            # 1. Metadatos de entidades
            placeholders = ",".join(["?"] * len(entity_ids))
            ent_meta_rows = cursor.execute(f"""
                SELECT ruc, razon_social, entity_type, segment, province_code, province_name,
                       total_assets_usd, first_period, last_period, is_active
                FROM read_parquet('{self._p("dim_entities")}')
                WHERE ruc IN ({placeholders});
            """, entity_ids).fetchall()

            entities_map = {}
            entities_list = []
            for r in ent_meta_rows:
                ent = EntitySummary(
                    ruc=r[0],
                    razon_social=r[1],
                    entity_type=r[2],
                    segment=r[3],
                    province=Province(code=r[4], name=r[5]) if r[4] else None,
                    total_assets_usd=float(r[6]) if r[6] is not None else None,
                    first_period=r[7],
                    last_period=r[8],
                    is_active=bool(r[9])
                )
                entities_map[r[0]] = ent
                entities_list.append(ent)

            for ruc in entity_ids:
                if ruc not in entities_map:
                    ent = EntitySummary(
                        ruc=ruc,
                        razon_social=f"Cooperativa RUC {ruc}",
                        entity_type="COOPERATIVA",
                        segment="SEGMENTO_1",
                        first_period=start_date,
                        last_period=end_date,
                        is_active=True
                    )
                    entities_list.append(ent)
                    entities_map[ruc] = ent

            # 2. Microdatos de entidades
            ent_data_rows = cursor.execute(f"""
                SELECT period, ruc, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_entity_monthly")}')
                WHERE ruc IN ({placeholders})
                  AND period >= ? AND period <= ?
                ORDER BY period ASC;
            """, entity_ids + [start_date, end_date]).fetchall()

            # 3. Línea Base Segmento 1
            seg_data_rows = cursor.execute(f"""
                SELECT period, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_segment_monthly")}')
                WHERE segment = 'SEGMENTO_1'
                  AND period >= ? AND period <= ?
                ORDER BY period ASC;
            """, [start_date, end_date]).fetchall()

            # 4. Línea Base País
            cty_data_rows = cursor.execute(f"""
                SELECT period, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                WHERE period >= ? AND period <= ?
                ORDER BY period ASC;
            """, [start_date, end_date]).fetchall()

        # Indexar Líneas Base
        seg_base: dict[str, dict[str, float | None]] = {}
        for period, ind_id, val in seg_data_rows:
            if ind_id in target_ids:
                if ind_id not in seg_base:
                    seg_base[ind_id] = {}
                seg_base[ind_id][period] = float(val) if val is not None else None

        cty_base: dict[str, dict[str, float | None]] = {}
        for period, ind_id, val in cty_data_rows:
            if ind_id in target_ids:
                if ind_id not in cty_base:
                    cty_base[ind_id] = {}
                cty_base[ind_id][period] = float(val) if val is not None else None

        # Indexar Entidades
        ent_series: dict[str, dict[str, dict[str, float | None]]] = {}
        ent_latest: dict[str, dict[str, tuple[str, float | None]]] = {}

        for period, ruc, ind_id, val in ent_data_rows:
            if ind_id in target_ids:
                if ind_id not in ent_series:
                    ent_series[ind_id] = {}
                if period not in ent_series[ind_id]:
                    ent_series[ind_id][period] = {}

                num_val = float(val) if val is not None else None
                ent_series[ind_id][period][ruc] = num_val

                if ind_id not in ent_latest:
                    ent_latest[ind_id] = {}
                ent_latest[ind_id][ruc] = (period, num_val)

        # Construir filas de indicadores
        indicator_rows: list[BenchmarkingIndicatorRow] = []
        time_series_by_indicator: dict[str, list[BenchmarkingSeriesPoint]] = {}

        for ind_meta in target_indicators:
            ind_id = ind_meta["id"]
            name = ind_meta.get("name", ind_id)
            dim = ind_meta.get("category", "calidad_de_activos")
            unit = ind_meta.get("unit", "percent")
            polarity: Polarity = ind_meta.get("polarity", "higher_is_better")
            ficha = ind_meta.get("seps_ficha_number")

            entity_vals: dict[str, float | None] = {}
            entity_evals: dict[str, Any] = {}

            for ruc in entity_ids:
                val_tuple = ent_latest.get(ind_id, {}).get(ruc)
                val = val_tuple[1] if val_tuple else None
                entity_vals[ruc] = round(val, 4) if val is not None else None

                evaluation = camel_evaluator.evaluate(
                    indicator_id=ind_id,
                    value=val,
                    default_polarity=polarity,
                    indicator_name=name
                )
                entity_evals[ruc] = evaluation

            seg_p_map = seg_base.get(ind_id, {})
            seg_latest_val = seg_p_map.get(end_date) if end_date in seg_p_map else (
                list(seg_p_map.values())[-1] if seg_p_map else None
            )

            cty_p_map = cty_base.get(ind_id, {})
            cty_latest_val = cty_p_map.get(end_date) if end_date in cty_p_map else (
                list(cty_p_map.values())[-1] if cty_p_map else None
            )

            row = BenchmarkingIndicatorRow(
                indicator_id=ind_id,
                indicator_name=name,
                dimension=dim,
                unit=unit,
                polarity=polarity,
                seps_ficha_number=ficha,
                entity_values=entity_vals,
                entity_evaluations=entity_evals,
                segment1_baseline=round(seg_latest_val, 4) if seg_latest_val is not None else None,
                country_baseline=round(cty_latest_val, 4) if cty_latest_val is not None else None
            )
            indicator_rows.append(row)

            periods_for_ind = sorted(list(
                set(ent_series.get(ind_id, {}).keys()) |
                set(seg_base.get(ind_id, {}).keys()) |
                set(cty_base.get(ind_id, {}).keys())
            ))

            pts: list[BenchmarkingSeriesPoint] = []
            for p in periods_for_ind:
                pt_entity_vals = {}
                for ruc in entity_ids:
                    pt_entity_vals[ruc] = ent_series.get(ind_id, {}).get(p, {}).get(ruc)

                pt = BenchmarkingSeriesPoint(
                    period=p,
                    entity_values=pt_entity_vals,
                    segment1_baseline=seg_base.get(ind_id, {}).get(p),
                    country_baseline=cty_base.get(ind_id, {}).get(p)
                )
                pts.append(pt)

            time_series_by_indicator[ind_id] = pts

        return BenchmarkingCompareResponse(
            entities=entities_list,
            start_date=start_date,
            end_date=end_date,
            camel_dimension=camel_dimension,
            indicators=indicator_rows,
            time_series=time_series_by_indicator,
            total_indicators=len(indicator_rows),
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    def get_entity_ranking(
        self,
        indicator_id: str,
        period: str | None = None,
        segment: str | None = None,
        province: str | None = None,
        rucs: list[str] | None = None,
        limit: int = 250
    ) -> BenchmarkingRankingResponse:
        """Calcula el ranking nacional de cooperativas ordenado según la polaridad y desempeño del ratio."""
        all_indicators = self.spec.get("indicators", [])
        ind_spec = next((i for i in all_indicators if i["id"] == indicator_id), None)
        if not ind_spec:
            raise APIProblemException(
                status_code=400,
                title="Indicador no encontrado",
                detail=f"El indicador '{indicator_id}' no existe en el catálogo oficial SEPS."
            )

        polarity: Polarity = ind_spec.get("polarity", "higher_is_better")
        if polarity == "lower_is_better":
            order_clause = "ORDER BY e.value ASC"
        elif polarity == "higher_is_better":
            order_clause = "ORDER BY e.value DESC"
        elif polarity == "neutral":
            thresh = camel_evaluator._config.get("indicators", {}).get(indicator_id, {}).get("thresholds", {})
            g_min = thresh.get("green_min", 75.0)
            g_max = thresh.get("green_max", 92.0)
            target_center = round((g_min + g_max) / 2.0, 2)
            order_clause = f"ORDER BY ABS(e.value - {target_center}) ASC"
        else:
            order_clause = "ORDER BY e.value DESC"

        with self.get_cursor() as cursor:
            if not period:
                max_p_row = cursor.execute(f"SELECT MAX(period) FROM read_parquet('{self._p('fct_indicators_country_monthly')}')").fetchone()
                period = max_p_row[0] if max_p_row and max_p_row[0] else "2025-12"

            s1_row = cursor.execute(f"""
                SELECT value FROM read_parquet('{self._p("fct_indicators_segment_monthly")}')
                WHERE segment = 'SEGMENTO_1' AND indicator_id = ? AND period = ?
            """, [indicator_id, period]).fetchone()
            s1_baseline = float(s1_row[0]) if (s1_row and s1_row[0] is not None) else None

            cty_row = cursor.execute(f"""
                SELECT value FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                WHERE indicator_id = ? AND period = ?
            """, [indicator_id, period]).fetchone()
            cty_baseline = float(cty_row[0]) if (cty_row and cty_row[0] is not None) else None

            params: list = [indicator_id, period]
            where_filters = []

            if segment and segment.strip() and segment.strip().upper() != "ALL":
                where_filters.append("segment = ?")
                params.append(segment.strip().upper())

            if province and province.strip() and province.strip().upper() != "ALL":
                where_filters.append("(UPPER(province) = UPPER(?) OR province_code = ?)")
                prov_clean = province.strip()
                params.extend([prov_clean, prov_clean])

            if rucs and len(rucs) > 0:
                clean_rucs = [r.strip() for r in rucs if r.strip()][:10]
                if clean_rucs:
                    placeholders = ", ".join(["?"] * len(clean_rucs))
                    where_filters.append(f"ruc IN ({placeholders})")
                    params.extend(clean_rucs)

            filter_sql = f"AND {' AND '.join(where_filters)}" if where_filters else ""

            query = f"""
                WITH ranked_national AS (
                    SELECT 
                        ROW_NUMBER() OVER ({order_clause}) AS nat_rank,
                        e.ruc,
                        COALESCE(dim.razon_social, e.ruc) AS razon_social,
                        COALESCE(dim.segment, 'SEGMENTO_1') AS segment,
                        COALESCE(dim.province_name, 'NACIONAL') AS province,
                        COALESCE(dim.province_code, '') AS province_code,
                        dim.total_assets_usd,
                        e.value
                    FROM read_parquet('{self._p_entity_partitioned()}', hive_partitioning=true) e
                    LEFT JOIN read_parquet('{self._p("dim_entities")}') dim ON e.ruc = dim.ruc
                    WHERE e.indicator_id = ? 
                      AND e.period = ?
                      AND e.value IS NOT NULL
                )
                SELECT 
                    nat_rank,
                    ruc,
                    razon_social,
                    segment,
                    province,
                    total_assets_usd,
                    value
                FROM ranked_national
                WHERE 1=1 {filter_sql}
                ORDER BY nat_rank ASC
                LIMIT ?;
            """
            params.append(limit)
            rows = cursor.execute(query, params).fetchall()

            ranking_items: list[EntityRankingItem] = []
            for rank_idx, r in enumerate(rows, start=1):
                nat_rank, ruc, razon, seg_code, prov, assets, val = r
                num_val = float(val)

                eval_item = camel_evaluator.evaluate(
                    indicator_id=indicator_id,
                    value=num_val,
                    default_polarity=polarity,
                    indicator_name=ind_spec.get("name")
                )

                diff_cty = round(num_val - cty_baseline, 4) if cty_baseline is not None else None
                diff_s1 = round(num_val - s1_baseline, 4) if s1_baseline is not None else None

                ranking_items.append(
                    EntityRankingItem(
                        rank=rank_idx,
                        national_rank=int(nat_rank),
                        ruc=ruc,
                        razon_social=razon,
                        segment=seg_code,
                        province=prov,
                        total_assets_usd=float(assets) if assets is not None else None,
                        value=round(num_val, 4),
                        camel_evaluation=eval_item,
                        diff_country=diff_cty,
                        diff_segment1=diff_s1
                    )
                )

            ind_meta_obj = IndicatorMeta(
                id=ind_spec["id"],
                name=ind_spec.get("name", ind_spec["id"]),
                short_name=ind_spec.get("short_name", ind_spec.get("name", ind_spec["id"])),
                category=ind_spec.get("category", "calidad_de_activos"),
                unit=ind_spec.get("unit", "percent"),
                decimals=ind_spec.get("decimals", 2),
                polarity=polarity,
                seps_ficha_number=ind_spec.get("seps_ficha_number"),
                latest_value=cty_baseline
            )

            return BenchmarkingRankingResponse(
                indicator=ind_meta_obj,
                period=period,
                segment_filter=segment if segment and segment.upper() != "ALL" else None,
                province_filter=province if province and province.upper() != "ALL" else None,
                selected_rucs=rucs if rucs else None,
                segment1_baseline=round(s1_baseline, 4) if s1_baseline is not None else None,
                country_baseline=round(cty_baseline, 4) if cty_baseline is not None else None,
                ranking=ranking_items,
                total_ranked=len(ranking_items),
                generated_at=datetime.now(timezone.utc).isoformat()
            )

    def extract_entity_microdata_rows(
        self,
        entity_ids: list[str],
        start_date: str,
        end_date: str,
        camel_dimension: str | None = None
    ) -> Generator[list[Any], None, None]:
        """Extrae microdatos tabulares en streaming/lotes combinando dimensiones y líneas base en DuckDB."""
        with self.get_cursor() as cursor:
            placeholders = ",".join(["?"] * len(entity_ids))
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
                WHERE e.ruc IN ({placeholders})
                  AND e.period >= ? AND e.period <= ?
                ORDER BY e.period ASC, e.indicator_id ASC, e.ruc ASC;
            """
            cursor.execute(query, entity_ids + [start_date, end_date])
            spec_map = {i["id"]: i for i in self.spec.get("indicators", [])}

            batch_size = 500
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for r in rows:
                    period, ruc, razon_social, segmento, provincia, ind_id, val, seg_val, cty_val = r
                    ind_spec = spec_map.get(ind_id, {})
                    dim = ind_spec.get("category", "calidad_de_activos")
                    if camel_dimension and dim != camel_dimension:
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
                    yield [
                        period,
                        ruc,
                        clean_coop,
                        razon_social,
                        segmento,
                        provincia,
                        ind_id,
                        ind_name,
                        dim,
                        round(float(val), 4) if val is not None else "",
                        round(float(seg_val), 4) if seg_val is not None else "",
                        round(float(cty_val), 4) if cty_val is not None else "",
                        eval_res.status,
                        eval_res.normative_reference,
                        eval_res.message
                    ]

# Instancia singleton del repositorio analítico consolidado
analytics_repository = AnalyticsRepository()
