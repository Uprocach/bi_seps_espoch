import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from etl.build_marts import build_marts


def _write_interim_parquet(path: Path, rows: list[tuple]) -> None:
    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE tmp_b11 (
            fecha_de_corte TIMESTAMP_NS,
            segmento VARCHAR,
            ruc VARCHAR,
            razon_social VARCHAR,
            cuenta VARCHAR,
            descripcion_cuenta VARCHAR,
            saldo__usd_ DOUBLE
        );
        """
    )
    con.executemany("INSERT INTO tmp_b11 VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    con.execute(f"COPY tmp_b11 TO '{path.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD);")


class TestBuildMartsQuarterly(unittest.TestCase):
    def test_quarterly_segments_marts_frequency_active_null_6digit_and_country_exclusion(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            men_dir = tmp / "men"
            trim_dir = tmp / "trim"
            mart_dir = tmp / "mart"
            men_dir.mkdir()
            trim_dir.mkdir()

            # Mensual: SEGMENTO 1 con 6 dígitos en 2026-09 y 2026-10
            men_rows = [
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "1", "ACTIVO", 1000.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "11", "FONDOS", 200.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "14", "CARTERA", 700.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "1425", "IMPR", 35.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "1499", "PROV", -40.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "2101", "VISTA", 400.0),
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1", "210305", "PLAZO", 100.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "1", "ACTIVO", 1050.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "11", "FONDOS", 210.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "14", "CARTERA", 720.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "1425", "IMPR", 36.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "1499", "PROV", -40.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "2101", "VISTA", 410.0),
                ("2026-10-31", "SEGMENTO 1", "0190155722001", "COAC S1", "210305", "PLAZO", 100.0),
            ]
            _write_interim_parquet(men_dir / "2026.parquet", men_rows)

            # Trimestral: SEGMENTO 4 y SEGMENTO 5 (4 dígitos) + fila SEGMENTO 1 que debe ser ignorada
            trim_rows = [
                ("2026-09-30", "SEGMENTO 1", "0190155722001", "COAC S1 DUP", "1", "ACTIVO", 999999.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "1", "ACTIVO", 500.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "11", "FONDOS", 100.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "14", "CARTERA", 300.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "1425", "IMPR", 15.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "1499", "PROV", -20.0),
                ("2026-09-30", "SEGMENTO 4", "0690000004001", "COAC S4", "2101", "VISTA", 250.0),
                ("2026-09-30", "SEGMENTO 5", "0690000005001", "COAC S5", "1", "ACTIVO", 200.0),
                ("2026-09-30", "SEGMENTO 5", "0690000005001", "COAC S5", "14", "CARTERA", 100.0),
                ("2026-09-30", "SEGMENTO 5", "0690000005001", "COAC S5", "1425", "IMPR", 5.0),
                ("2026-09-30", "SEGMENTO 5", "0690000005001", "COAC S5", "1499", "PROV", -5.0),
            ]
            _write_interim_parquet(trim_dir / "2026_trim.parquet", trim_rows)

            build_marts(target_dir=mart_dir, interim_dir=men_dir, interim_trim_dir=trim_dir)

            con = duckdb.connect()
            freqs = dict(
                con.execute(
                    f"SELECT code, reporting_frequency FROM read_parquet('{(mart_dir / 'dim_segments.parquet').as_posix()}')"
                ).fetchall()
            )
            self.assertEqual(freqs["SEGMENTO_4"], "quarterly")
            self.assertEqual(freqs["SEGMENTO_5"], "quarterly")
            self.assertEqual(freqs["SEGMENTO_1"], "monthly")

            entities = {
                r[0]: r[1:]
                for r in con.execute(
                    f"SELECT ruc, segment, total_assets_usd, last_period, is_active FROM read_parquet('{(mart_dir / 'dim_entities.parquet').as_posix()}')"
                ).fetchall()
            }
            self.assertEqual(entities["0690000004001"], ("SEGMENTO_4", 500.0, "2026-09", True))
            self.assertEqual(entities["0690000005001"], ("SEGMENTO_5", 200.0, "2026-09", True))

            # Liquidez (6 dígitos) debe ser NULL para Seg 4, y calculada para Seg 1
            liq_s4 = con.execute(
                f"SELECT value, numerator, denominator FROM read_parquet('{(mart_dir / 'fct_indicators_entity_monthly.parquet').as_posix()}') WHERE ruc='0690000004001' AND indicator_id='liquidez_inmediata'"
            ).fetchone()
            self.assertEqual(liq_s4, (None, None, None))

            # País (EC) en 2026-09 solo debe contar la entidad mensual (entity_count = 1)
            ec_row = con.execute(
                f"SELECT entity_count FROM read_parquet('{(mart_dir / 'fct_indicators_country_monthly.parquet').as_posix()}') WHERE period='2026-09' AND indicator_id='morosidad_cartera_total'"
            ).fetchone()
            self.assertEqual(ec_row[0], 1)


if __name__ == "__main__":
    unittest.main()
