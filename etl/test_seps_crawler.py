import io
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from etl.seps_crawler import SepsCrawler


class TestSepsCrawlerQuarterly(unittest.TestCase):
    def test_discover_downloads_detects_quarterly_bases_and_ignores_xlsm_reports(self):
        html = """
        <html><body>
          <h2>Estados Financieros Mensuales</h2>
          <h3>Bases de Datos</h3>
          <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=3401">2026</a>
          <h2>Estados Financieros Trimestrales</h2>
          <h3>Reportes</h3>
          <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=3434">2026</a>
          <h3>Bases de Datos</h3>
          <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=3443">2026</a>
          <a href="https://estadisticas.seps.gob.ec/?sdm_process_download=1&download_id=2961">2025</a>
        </body></html>
        """
        crawler = SepsCrawler()
        crawler.fetch_portal_html = lambda timeout=20: html  # type: ignore[method-assign]

        catalog = crawler.discover_downloads()

        self.assertEqual(catalog["eeff_mensuales_bases"], {2026: 3401})
        self.assertIn("eeff_trimestrales_bases", catalog)
        self.assertEqual(catalog["eeff_trimestrales_bases"], {2026: 3443, 2025: 2961})
        self.assertEqual(catalog["eeff_trimestrales_reportes"], {2026: 3434})

    def test_extract_quarterly_handles_csv_saldo_no_space_extra_col_unpadded_date_and_segment_filter(self):
        tsv_content = (
            "FECHA DE CORTE\tSEGMENTO\tRUC\tRAZON SOCIAL\tCUENTA\tDESCRIPCION CUENTA\tSALDO(USD)\tDW CUENTAS.Desglose\n"
            "2022-6-30\tSEGMENTO 1\t0190155722001\tCOAC SEG 1\t1\tACTIVO\t1000,50\tDETALLE\n"
            "2022-6-30\tSEGMENTO 4\t0690000004001\tCOAC SEG 4\t1\tACTIVO\t2500,75\tDETALLE\n"
            "2022-9-30\tSEGMENTO 5\t0690000005001\tCOAC SEG 5\t14\tCARTERA\t1200,00\tDETALLE\n"
        )
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            zip_path = tmp / "2020_trim.zip"
            out_parquet = tmp / "eeff_trim_2020.parquet"
            with zipfile.ZipFile(zip_path, "w") as z:
                z.writestr("2020.csv", tsv_content.encode("utf-8"))

            crawler = SepsCrawler()
            meta = crawler.extract_eeff_b11_to_parquet(
                zip_path,
                out_parquet,
                segments_filter=["SEGMENTO 4", "SEGMENTO 5"],
            )

            self.assertEqual(meta["records"], 2)
            rows = duckdb.read_parquet(str(out_parquet)).fetchall()
            segments = {r[1] for r in rows}
            self.assertEqual(segments, {"SEGMENTO 4", "SEGMENTO 5"})
            saldos = sorted(r[6] for r in rows)
            self.assertEqual(saldos, [1200.0, 2500.75])

    def test_sync_processes_both_monthly_and_quarterly_bases(self):
        from etl.seps_crawler import QUARTERLY_SEGMENTS

        crawler = SepsCrawler()
        crawler.discover_downloads = lambda: {  # type: ignore[method-assign]
            "eeff_mensuales_bases": {2026: 3401},
            "eeff_trimestrales_bases": {2026: 3443},
            "patrimonio_tecnico": {},
            "eeff_mensuales_reportes": {},
            "eeff_trimestrales_reportes": {},
            "latest_year_available": 2026,
            "total_links_found": 2,
        }
        crawler.download_file = lambda d_id, dest, **kwargs: dest  # type: ignore[method-assign]
        extracted_calls = []

        def fake_extract(zip_path, out_parquet, segments_filter=None):
            extracted_calls.append((zip_path.name, out_parquet.name, segments_filter))
            return {"records": 10, "min_date": "2026-01-01", "max_date": "2026-09-30", "file_size": 100, "parquet_path": str(out_parquet)}

        crawler.extract_eeff_b11_to_parquet = fake_extract  # type: ignore[method-assign]

        res = crawler.sync(force=True)
        self.assertEqual(res["status"], "success")
        types = {f["type"] for f in res["updated_files"]}
        self.assertIn("b11_balances", types)
        self.assertIn("b11_trimestrales", types)
        trim_call = next(c for c in extracted_calls if c[1].startswith("eeff_trim_"))
        self.assertEqual(trim_call[2], QUARTERLY_SEGMENTS)


if __name__ == "__main__":
    unittest.main()
