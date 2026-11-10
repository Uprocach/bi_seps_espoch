import json
import duckdb
from contextlib import contextmanager
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.errors import APIProblemException

class AnalyticsRepository:
    ALLOWED_SORT_FIELDS = {
        "total_assets_usd": "total_assets_usd",
        "razon_social": "razon_social",
        "ruc": "ruc",
        "first_period": "first_period",
        "last_period": "last_period"
    }

    def __init__(self, mart_dir: Path | None = None):
        self.mart_dir = mart_dir or settings.DATA_MART_DIR
        self.spec = self._load_spec()
        self._con = duckdb.connect()
        self._con.execute("PRAGMA threads=4;")

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
        return str(self.mart_dir / f"{name}.parquet").replace("\\", "/")

    def _p_entity_partitioned(self) -> str:
        """Ruta al árbol de particiones Hive en Parquet para optimizar consultas de microdatos con partition pruning."""
        partitioned_path = self.mart_dir / "partitioned" / "fct_indicators_entity"
        if partitioned_path.exists():
            return str(partitioned_path / "*/*/*.parquet").replace("\\", "/")
        return self._p("fct_indicators_entity_monthly")

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
