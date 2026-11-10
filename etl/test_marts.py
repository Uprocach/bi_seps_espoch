"""
Test Suite: Validación de Calidad e Integridad de Data Marts (DuckDB)
Verifica integridad referencial, consistencia matemática y contratos OpenAPI.
"""

import sys
import unittest
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
import os
MART_DIR = Path(os.getenv("MART_DIR", str(BASE_DIR / "data" / "processed" / "mart")))

class TestDataMarts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = duckdb.connect()
        cls.marts = {
            "provinces": str(MART_DIR / "dim_provinces.parquet").replace("\\", "/"),
            "segments": str(MART_DIR / "dim_segments.parquet").replace("\\", "/"),
            "entities": str(MART_DIR / "dim_entities.parquet").replace("\\", "/"),
            "entity_fct": str(MART_DIR / "fct_indicators_entity_monthly.parquet").replace("\\", "/"),
            "segment_fct": str(MART_DIR / "fct_indicators_segment_monthly.parquet").replace("\\", "/"),
            "country_fct": str(MART_DIR / "fct_indicators_country_monthly.parquet").replace("\\", "/")
        }

    def test_dimensions_loaded(self):
        """Verifica que las dimensiones estáticas tengan el número esperado de filas."""
        n_provinces = self.con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.marts['provinces']}')").fetchone()[0]
        self.assertEqual(n_provinces, 24, "Deben existir exactamente 24 provincias.")

        n_segments = self.con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.marts['segments']}')").fetchone()[0]
        self.assertEqual(n_segments, 6, "Deben existir 6 segmentos.")

        n_entities = self.con.execute(f"SELECT COUNT(*) FROM read_parquet('{self.marts['entities']}')").fetchone()[0]
        self.assertGreaterEqual(n_entities, 200, "Deben existir al menos 200 entidades registradas.")

    def test_entity_integrity(self):
        """Verifica que los RUCs y provincias de dim_entities sean 100% válidos."""
        invalid_rucs = self.con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{self.marts['entities']}')
            WHERE length(ruc) != 13 OR NOT ruc LIKE '%001'
        """).fetchone()[0]
        self.assertEqual(invalid_rucs, 0, "Todos los RUCs deben tener 13 dígitos y terminar en 001.")

        null_provinces = self.con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{self.marts['entities']}')
            WHERE province_code IS NULL OR province_name IS NULL
        """).fetchone()[0]
        self.assertEqual(null_provinces, 0, "Ninguna entidad debe tener provincia nula.")

    def test_mathematical_consistency(self):
        """Verifica que el ratio calculado sea exactamente igual a (numerador / denominador) * 100."""
        # Se permiten casos donde el denominador es 0 o negativo y el valor es NULL
        discrepancies = self.con.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{self.marts['entity_fct']}')
            WHERE denominator > 0 
              AND value IS NOT NULL
              AND abs(value - round((numerator / denominator) * 100, 4)) > 0.001
        """).fetchone()[0]
        self.assertEqual(discrepancies, 0, "No debe haber discrepancias en la fórmula de ratio de entidad.")

    def test_country_aggregation_reconciliation(self):
        """Verifica que la agregación país sea exactamente la suma de numeradores y denominadores de entidades."""
        reconciled = self.con.execute(f"""
            WITH ent AS (
                SELECT period, indicator_id, round(sum(numerator), 2) AS sum_num, round(sum(denominator), 2) AS sum_den
                FROM read_parquet('{self.marts['entity_fct']}')
                WHERE period = '2025-12' AND indicator_id = 'morosidad_cartera_total'
                GROUP BY period, indicator_id
            ),
            cty AS (
                SELECT period, indicator_id, numerator, denominator
                FROM read_parquet('{self.marts['country_fct']}')
                WHERE period = '2025-12' AND indicator_id = 'morosidad_cartera_total'
            )
            SELECT abs(ent.sum_num - cty.numerator), abs(ent.sum_den - cty.denominator)
            FROM ent JOIN cty ON ent.period = cty.period AND ent.indicator_id = cty.indicator_id
        """).fetchone()
        
        self.assertIsNotNone(reconciled)
        self.assertAlmostEqual(reconciled[0], 0.0, places=1, msg="Numerador país no concilia con suma de entidades.")
        self.assertAlmostEqual(reconciled[1], 0.0, places=1, msg="Denominador país no concilia con suma de entidades.")

    def test_realistic_indicator_ranges(self):
        """Verifica que los indicadores caigan en rangos financieros económicamente lógicos."""
        morosidad_corte_2025 = self.con.execute(f"""
            SELECT value FROM read_parquet('{self.marts['country_fct']}')
            WHERE period = '2025-12' AND indicator_id = 'morosidad_cartera_total'
        """).fetchone()[0]
        # Morosidad de cartera total del sector cooperativo está en torno al 7-9% a dic 2025
        self.assertTrue(5.0 <= morosidad_corte_2025 <= 12.0, f"Morosidad país ({morosidad_corte_2025}%) fuera de rango razonable.")

        cobertura_corte_2025 = self.con.execute(f"""
            SELECT value FROM read_parquet('{self.marts['country_fct']}')
            WHERE period = '2025-12' AND indicator_id = 'cobertura_cartera_improductiva'
        """).fetchone()[0]
        # Cobertura de cartera suele estar alrededor del 100%-120%
        self.assertTrue(90.0 <= cobertura_corte_2025 <= 130.0, f"Cobertura país ({cobertura_corte_2025}%) fuera de rango razonable.")

if __name__ == "__main__":
    unittest.main()
