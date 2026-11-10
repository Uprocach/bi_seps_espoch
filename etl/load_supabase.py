"""
Loader: Sincronización de Data Marts hacia Supabase (PostgreSQL)
Permite carga directa por conexión Postgres o generación de dump SQL / CSV para importación.
"""

import os
import sys
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parent.parent
MART_DIR = BASE_DIR / "data" / "processed" / "mart"
SCHEMA_SQL_PATH = BASE_DIR / "contracts" / "supabase_schema.sql"

def generate_sql_dump(output_file: Path):
    """Genera un archivo de seed SQL completo listo para ejecutar en Supabase SQL Editor."""
    con = duckdb.connect()
    with open(output_file, "w", encoding="utf-8") as out:
        # 1. Esquema
        out.write("-- AUTO-GENERATED SEED DUMP FOR SUPABASE\n")
        out.write(open(SCHEMA_SQL_PATH, "r", encoding="utf-8").read())
        out.write("\n\n-- SEED DATA\n")

        # 2. Datos de dimensiones
        for dim in ["dim_provinces", "dim_segments", "dim_entities"]:
            p = str(MART_DIR / f"{dim}.parquet").replace("\\", "/")
            res = con.execute(f"SELECT * FROM read_parquet('{p}')")
            cols = [d[0] for d in res.description]
            rows = res.fetchall()
            out.write(f"\n-- {dim} ({len(rows)} filas)\n")
            for row in rows:
                vals = []
                for val in row:
                    if val is None:
                        vals.append("NULL")
                    elif isinstance(val, bool):
                        vals.append("TRUE" if val else "FALSE")
                    elif isinstance(val, (int, float)):
                        vals.append(str(val))
                    else:
                        clean_str = str(val).replace("'", "''")
                        vals.append(f"'{clean_str}'")
                out.write(f"INSERT INTO {dim} ({', '.join(cols)}) VALUES ({', '.join(vals)}) ON CONFLICT DO NOTHING;\n")
        
        print(f"✓ SQL Dump generado exitosamente en: {output_file}")

def load_to_postgres(db_url: str):
    """Carga masiva hacia Postgres vía DuckDB Postgres Extension o psycopg."""
    print(f"Conectando a base de datos de producción: {db_url[:20]}...")
    con = duckdb.connect()
    try:
        con.execute("INSTALL postgres; LOAD postgres;")
        con.execute(f"ATTACH '{db_url}' AS pg (TYPE POSTGRES);")
        
        # Ejecutar DDL
        ddl = open(SCHEMA_SQL_PATH, "r", encoding="utf-8").read()
        con.execute(f"USE pg; {ddl}")
        
        # Copiar tablas
        for tbl in ["dim_provinces", "dim_segments", "dim_entities", 
                    "fct_indicators_entity_monthly", "fct_indicators_segment_monthly", "fct_indicators_country_monthly"]:
            p = str(MART_DIR / f"{tbl}.parquet").replace("\\", "/")
            print(f"Cargando {tbl} hacia Supabase...")
            con.execute(f"INSERT INTO pg.{tbl} SELECT * FROM read_parquet('{p}') ON CONFLICT DO NOTHING;")
        print("✓ Carga a Supabase completada con éxito.")
    except Exception as e:
        print(f"Aviso de conexión: {e}")
        print("Generando SQL seed de respaldo...")
        generate_sql_dump(MART_DIR / "supabase_seed.sql")

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if db_url:
        load_to_postgres(db_url)
    else:
        print("No se detectó DATABASE_URL ni SUPABASE_DB_URL en el entorno.")
        print("Generando archivo SQL Seed para carga manual o posterior...")
        generate_sql_dump(MART_DIR / "supabase_seed.sql")
