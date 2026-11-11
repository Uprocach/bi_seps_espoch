from pathlib import Path
import duckdb
from backend.app.core.config import settings

class MartPathProvider:
    """Proveedor centralizado de resolución de rutas Parquet y conexiones DuckDB (AUD-17).
    
    Elimina la duplicación de lógica entre AnalyticsRepository, BenchmarkingService y ExportService,
    facilitando el futuro reemplazo atómico de datos en caliente (Zero-Downtime Mart Switch).
    """

    def __init__(self, mart_dir: Path | None = None):
        self.mart_dir = mart_dir or settings.DATA_MART_DIR

    def p(self, name: str) -> str:
        """Retorna la ruta normalizada con barras diagonales de un dataset Parquet en el mart."""
        return str(self.mart_dir / f"{name}.parquet").replace("\\", "/")

    def p_entity_partitioned(self) -> str:
        """Ruta al árbol de particiones Hive en Parquet para optimizar partition pruning."""
        partitioned_path = self.mart_dir / "partitioned" / "fct_indicators_entity"
        if partitioned_path.exists():
            return str(partitioned_path / "*/*/*.parquet").replace("\\", "/")
        return self.p("fct_indicators_entity_monthly")

    def create_connection(self, threads: int = 4) -> duckdb.DuckDBPyConnection:
        """Crea y configura una conexión DuckDB optimizada para consultas analíticas multihilo."""
        con = duckdb.connect()
        con.execute(f"PRAGMA threads={threads};")
        return con

mart_provider = MartPathProvider()
