import json
import duckdb
from datetime import datetime, timezone
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.errors import APIProblemException
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

class BenchmarkingService:
    """Motor analítico de benchmarking multi-entidad en DuckDB para la Capa Pro."""

    def __init__(self, mart_dir: Path | None = None):
        self.mart_dir = mart_dir or settings.DATA_MART_DIR
        self.spec = self._load_spec()
        self._con = duckdb.connect()
        self._con.execute("PRAGMA threads=4;")

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

    def get_cursor(self):
        return self._con.cursor()

    def compare(self, req: BenchmarkingCompareRequest) -> BenchmarkingCompareResponse:
        """Contrasta hasta 5 cooperativas simultáneamente contra las líneas base del Segmento 1 y la media nacional."""
        entity_ids = req.entity_ids
        start_date = req.start_date
        end_date = req.end_date
        camel_dimension = req.camel_dimension

        # Filtrar indicadores aplicables según dimensión solicitada
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
        target_map = {i["id"]: i for i in target_indicators}

        with self.get_cursor() as cursor:
            # 1. Obtener Metadatos de las Entidades seleccionadas
            ruc_in_clause = ",".join([f"'{ruc}'" for ruc in entity_ids])
            ent_meta_rows = cursor.execute(f"""
                SELECT ruc, razon_social, entity_type, segment, province_code, province_name,
                       total_assets_usd, first_period, last_period, is_active
                FROM read_parquet('{self._p("dim_entities")}')
                WHERE ruc IN ({ruc_in_clause});
            """).fetchall()

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

            # Si alguna entidad no está en dim_entities, crear placeholder informativo
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

            # 2. Consultar Microdatos de Entidades seleccionadas (Parquet fct_indicators_entity_monthly)
            ent_data_rows = cursor.execute(f"""
                SELECT period, ruc, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_entity_monthly")}')
                WHERE ruc IN ({ruc_in_clause})
                  AND period >= ? AND period <= ?
                ORDER BY period ASC;
            """, [start_date, end_date]).fetchall()

            # 3. Consultar Línea Base Segmento 1
            seg_data_rows = cursor.execute(f"""
                SELECT period, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_segment_monthly")}')
                WHERE segment = 'SEGMENTO_1'
                  AND period >= ? AND period <= ?
                ORDER BY period ASC;
            """, [start_date, end_date]).fetchall()

            # 4. Consultar Línea Base País (Media Nacional)
            cty_data_rows = cursor.execute(f"""
                SELECT period, indicator_id, value
                FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                WHERE period >= ? AND period <= ?
                ORDER BY period ASC;
            """, [start_date, end_date]).fetchall()

        # Indexar Líneas Base en memoria
        # Estructura: seg_base[indicator_id][period] = float
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

        # Indexar Datos de Entidades
        # Estructura: ent_series[indicator_id][period][ruc] = float
        # Estructura: ent_latest[indicator_id][ruc] = (latest_period, float)
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
                # Como vienen ordenados ascendentemente, el último asignado es el más reciente
                ent_latest[ind_id][ruc] = (period, num_val)

        # Construir Filas de Indicadores con Semáforos Inteligentes
        indicator_rows: list[BenchmarkingIndicatorRow] = []
        time_series_by_indicator: dict[str, list[BenchmarkingSeriesPoint]] = {}

        for ind_meta in target_indicators:
            ind_id = ind_meta["id"]
            name = ind_meta.get("name", ind_id)
            dim = ind_meta.get("category", "calidad_de_activos")
            unit = ind_meta.get("unit", "percent")
            polarity: Polarity = ind_meta.get("polarity", "higher_is_better")
            ficha = ind_meta.get("seps_ficha_number")

            # Valores más recientes y evaluaciones de semáforo para cada cooperativa
            entity_vals: dict[str, float | None] = {}
            entity_evals: dict[str, Any] = {}

            for ruc in entity_ids:
                val_tuple = ent_latest.get(ind_id, {}).get(ruc)
                val = val_tuple[1] if val_tuple else None
                entity_vals[ruc] = round(val, 4) if val is not None else None

                # Evaluar semáforo regulatorio
                evaluation = camel_evaluator.evaluate(
                    indicator_id=ind_id,
                    value=val,
                    default_polarity=polarity,
                    indicator_name=name
                )
                entity_evals[ruc] = evaluation

            # Líneas base del periodo de corte más reciente
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

            # Construir puntos de serie temporal mensual completa
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
        """Calcula el ranking nacional de cooperativas ordenado según la polaridad y desempeño del ratio, con soporte para provincia y grupo de hasta 10 COACs."""
        all_indicators = self.spec.get("indicators", [])
        ind_spec = next((i for i in all_indicators if i["id"] == indicator_id), None)
        if not ind_spec:
            raise APIProblemException(
                status_code=400,
                title="Indicador no encontrado",
                detail=f"El indicador '{indicator_id}' no existe en el catálogo oficial SEPS."
            )

        polarity: Polarity = ind_spec.get("polarity", "higher_is_better")
        
        # Rigurosa polaridad vectorial para el ranking:
        # - lower_is_better: menor valor = ranking #1 (ej. morosidad, gastos)
        # - higher_is_better: mayor valor = ranking #1 (ej. solvencia, ROA, liquidez)
        # - neutral: óptimo en el centro del rango prudencial (ej. intermediación financiera 75%-92%, centro = 83.5%)
        #   Se ordena según la menor distancia absoluta al centro normativo |value - target_center| ASC.
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

            # Línea Base Segmento 1
            s1_row = cursor.execute(f"""
                SELECT value FROM read_parquet('{self._p("fct_indicators_segment_monthly")}')
                WHERE segment = 'SEGMENTO_1' AND indicator_id = ? AND period = ?
            """, [indicator_id, period]).fetchone()
            s1_baseline = float(s1_row[0]) if (s1_row and s1_row[0] is not None) else None

            # Línea Base País
            cty_row = cursor.execute(f"""
                SELECT value FROM read_parquet('{self._p("fct_indicators_country_monthly")}')
                WHERE indicator_id = ? AND period = ?
            """, [indicator_id, period]).fetchone()
            cty_baseline = float(cty_row[0]) if (cty_row and cty_row[0] is not None) else None

            # Construir filtros dinámicos preservando el ranking nacional absoluto (nat_rank)
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

# Instancia singleton del servicio
benchmarking_service = BenchmarkingService()
