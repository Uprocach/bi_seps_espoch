"""
ETL Pipeline: Construcción de Data Marts para Indicadores Financieros SFPS (SEPS)
Motor: DuckDB en memoria con salida a Apache Parquet (Directorio particionado y marts consolidados).
Genera las 63 Fichas Metodológicas Oficiales de la SEPS.
"""

import sys
import os
import json
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INTERIM_DIR = Path(os.getenv("INTERIM_DIR", str(BASE_DIR / "data" / "interim" / "situacion_financiera" / "estados_financieros_mensuales")))
MART_DIR = Path(os.getenv("MART_DIR", str(BASE_DIR / "data" / "processed" / "mart")))
SPEC_PATH = BASE_DIR / "config" / "indicators_spec.json"

PROVINCES_DEF = [
    {"code": "01", "name": "AZUAY"},
    {"code": "02", "name": "BOLIVAR"},
    {"code": "03", "name": "CANAR"},
    {"code": "04", "name": "CARCHI"},
    {"code": "05", "name": "COTOPAXI"},
    {"code": "06", "name": "CHIMBORAZO"},
    {"code": "07", "name": "EL ORO"},
    {"code": "08", "name": "ESMERALDAS"},
    {"code": "09", "name": "GUAYAS"},
    {"code": "10", "name": "IMBABURA"},
    {"code": "11", "name": "LOJA"},
    {"code": "12", "name": "LOS RIOS"},
    {"code": "13", "name": "MANABI"},
    {"code": "14", "name": "MORONA SANTIAGO"},
    {"code": "15", "name": "NAPO"},
    {"code": "16", "name": "PASTAZA"},
    {"code": "17", "name": "PICHINCHA"},
    {"code": "18", "name": "TUNGURAHUA"},
    {"code": "19", "name": "ZAMORA CHINCHIPE"},
    {"code": "20", "name": "GALAPAGOS"},
    {"code": "21", "name": "SUCUMBIOS"},
    {"code": "22", "name": "ORELLANA"},
    {"code": "23", "name": "SANTO DOMINGO DE LOS TSACHILAS"},
    {"code": "24", "name": "SANTA ELENA"}
]

SEGMENTS_DEF = [
    {"code": "SEGMENTO_1", "label": "Segmento 1", "reporting_frequency": "monthly"},
    {"code": "SEGMENTO_2", "label": "Segmento 2", "reporting_frequency": "monthly"},
    {"code": "SEGMENTO_3", "label": "Segmento 3", "reporting_frequency": "monthly"},
    {"code": "SEGMENTO_4", "label": "Segmento 4", "reporting_frequency": "monthly"},
    {"code": "SEGMENTO_5", "label": "Segmento 5", "reporting_frequency": "monthly"},
    {"code": "SEGMENTO_1_MUTUALISTA", "label": "Mutualistas Segmento 1", "reporting_frequency": "monthly"}
]

def build_marts(target_dir: Path | None = None):
    out_dir = Path(target_dir) if target_dir else Path(os.getenv("MART_DIR", str(BASE_DIR / "data" / "processed" / "mart")))
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=4;")

    with open(SPEC_PATH, "r", encoding="utf-8") as f:
        spec = json.load(f)
    
    impr_accounts = spec["components"]["cartera_improductiva"]["accounts"]
    impr_sql_list = ", ".join(f"'{acc}'" for acc in impr_accounts)

    print("[1/6] Creando dimensiones...")
    con.execute("CREATE TABLE dim_provinces (code VARCHAR PRIMARY KEY, name VARCHAR);")
    for p in PROVINCES_DEF:
        con.execute(f"INSERT INTO dim_provinces VALUES ('{p['code']}', '{p['name']}');")
    
    con.execute("CREATE TABLE dim_segments (code VARCHAR PRIMARY KEY, label VARCHAR, reporting_frequency VARCHAR);")
    for s in SEGMENTS_DEF:
        con.execute(f"INSERT INTO dim_segments VALUES ('{s['code']}', '{s['label']}', '{s['reporting_frequency']}');")

    interim_pattern = str(INTERIM_DIR / "*.parquet").replace("\\", "/")
    print(f"[2/6] Escaneando y pivoteando balances B11...")
    
    con.execute(f"""
    CREATE TABLE raw_balances AS
    SELECT 
        COALESCE("\ufefffecha_de_corte", fecha_de_corte)::DATE AS fecha,
        STRFTIME(COALESCE("\ufefffecha_de_corte", fecha_de_corte)::DATE, '%Y-%m') AS period,
        ruc,
        ANY_VALUE(razon_social) AS razon_social,
        CASE 
            WHEN ANY_VALUE(segmento) ILIKE '%MUTUALISTA%' THEN 'SEGMENTO_1_MUTUALISTA'
            WHEN ANY_VALUE(segmento) ILIKE '%SEGMENTO 1%' THEN 'SEGMENTO_1'
            WHEN ANY_VALUE(segmento) ILIKE '%SEGMENTO 2%' THEN 'SEGMENTO_2'
            WHEN ANY_VALUE(segmento) ILIKE '%SEGMENTO 3%' THEN 'SEGMENTO_3'
            WHEN ANY_VALUE(segmento) ILIKE '%SEGMENTO 4%' THEN 'SEGMENTO_4'
            WHEN ANY_VALUE(segmento) ILIKE '%SEGMENTO 5%' THEN 'SEGMENTO_5'
            ELSE 'SEGMENTO_3'
        END AS segment,
        SUBSTRING(ruc, 1, 2) AS province_code,
        -- Cuentas generales
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '1') AS c1,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '11') AS c11,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '14') AS c14,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '1499') AS c1499,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ({impr_sql_list})) AS cartera_improductiva,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '21') AS c21,
        -- AUD-07: Depósitos a corto plazo (1 a 90 días y vista) según Ficha 52 SEPS
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('2101', '2102', '210305', '210310')) AS depo_corto_plazo,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('2101', '2102', '2103', '2104', '2105', '22', '23', '24', '25', '26', '27', '28')) AS pasivo_con_costo,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '3') AS c3,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '4') AS c4,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '45') AS c45,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '5') AS c5,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '3603') AS c3603,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '3604') AS c3604,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '16') AS c16,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '17') AS c17,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '18') AS c18,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '19') AS c19,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '1901') AS c1901,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '4501') AS c4501,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '51') AS c51,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '41') AS c41,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '52') AS c52,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '54') AS c54,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '42') AS c42,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '53') AS c53,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '43') AS c43,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '44') AS c44,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '56') AS c56,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '5104') AS c5104,
        -- Morosidades específicas
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1425','1433','1441','1449','1457','1465')) AS impr_comer_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1401','1409','1417','1425','1433','1441','1449','1457','1465')) AS bruta_comer_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1426','1434','1442','1450','1458','1466')) AS impr_consu_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1402','1410','1418','1426','1434','1442','1450','1458','1466')) AS bruta_consu_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1427','1435','1443','1451','1459','1467')) AS impr_inmob,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1403','1411','1419','1427','1435','1443','1451','1459','1467')) AS bruta_inmob,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1428','1436','1444','1452','1460','1468')) AS impr_micro,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1404','1412','1420','1428','1436','1444','1452','1460','1468')) AS bruta_micro,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1429','1437','1445','1453','1461','1469')) AS impr_prod,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1405','1413','1421','1429','1437','1445','1453','1461','1469')) AS bruta_prod,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1430','1438','1446','1454','1462','1470')) AS impr_comer_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1406','1414','1422','1430','1438','1446','1454','1462','1470')) AS bruta_comer_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1431','1439','1447','1455','1463','1471')) AS impr_consu_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1407','1415','1423','1431','1439','1447','1455','1463','1471')) AS bruta_consu_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1432','1440','1448','1456','1464','1472')) AS impr_viv_pub,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1408','1416','1424','1432','1440','1448','1456','1464','1472')) AS bruta_viv_pub,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1479','1481','1483','1485','1487','1489')) AS impr_educ,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1473','1475','1477','1479','1481','1483','1485','1487','1489')) AS bruta_educ,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1426','1434','1442','1450','1458','1466','1431','1439','1447','1455','1463','1471')) AS impr_consu,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1402','1410','1418','1426','1434','1442','1450','1458','1466','1407','1415','1423','1431','1439','1447','1455','1463','1471')) AS bruta_consu,
        -- Provisiones de cartera específicas (CUC 1499xx en valor absoluto)
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149905')) AS prov_prod,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149910')) AS prov_consu,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149915')) AS prov_inmob,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149920')) AS prov_micro,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149925')) AS prov_prod_esp,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149930')) AS prov_comer_ord,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149935')) AS prov_consu_ord,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149940')) AS prov_viv_pub,
        ABS(SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '149955')) AS prov_educ,
        -- Cuentas de intereses de cartera por vencer (5104xx)
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510405') AS c510405,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510410') AS c510410,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510415') AS c510415,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510420') AS c510420,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510421') AS c510421,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510425') AS c510425,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510426') AS c510426,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510427') AS c510427,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510428') AS c510428,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510430') AS c510430,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta = '510435') AS c510435,
        -- Carteras por vencer específicas
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1401','1409','1417')) AS xvenc_comer_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1402','1410','1418')) AS xvenc_consu_pri,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1403','1411','1419')) AS xvenc_inmob,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1404','1412','1420')) AS xvenc_micro,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1405','1413','1421')) AS xvenc_prod,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1406','1414','1422')) AS xvenc_comer_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1407','1415','1423')) AS xvenc_consu_ord,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1408','1416','1424')) AS xvenc_viv_pub,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1473','1475','1477')) AS xvenc_educ,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1409','1410','1411','1412','1413','1414','1415','1416')) AS xvenc_refi,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1417','1418','1419','1420','1421','1422','1423','1424','1477')) AS xvenc_rest,
        SUM(COALESCE(saldo_usd, saldo__usd_, 0)) FILTER (WHERE cuenta IN ('1401','1409','1417','1402','1410','1418','1403','1411','1419','1404','1412','1420','1405','1413','1421','1406','1414','1422','1407','1415','1423','1408','1416','1424','1473','1475','1477')) AS cartera_x_vencer
    FROM read_parquet('{interim_pattern}', union_by_name=true)
    WHERE ruc IS NOT NULL AND ruc != ''
    GROUP BY 1, 2, 3
    """)

    print("[3/6] Construyendo dimensión de entidades (dim_entities)...")
    latest_period = con.execute("SELECT MAX(period) FROM raw_balances;").fetchone()[0]
    
    con.execute(f"""
    CREATE TABLE dim_entities AS
    WITH agg AS (
        SELECT 
            ruc,
            ANY_VALUE(razon_social) AS razon_social,
            ANY_VALUE(segment) AS segment,
            ANY_VALUE(province_code) AS province_code,
            MIN(period) AS first_period,
            MAX(period) AS last_period
        FROM raw_balances
        GROUP BY ruc
    ),
    latest AS (
        SELECT ruc, c1 AS total_assets_usd
        FROM raw_balances
        WHERE period = '{latest_period}'
    )
    SELECT 
        a.ruc,
        a.razon_social,
        CASE WHEN a.segment = 'SEGMENTO_1_MUTUALISTA' THEN 'MUTUALISTA' ELSE 'COOPERATIVA' END AS entity_type,
        a.segment,
        a.province_code,
        p.name AS province_name,
        COALESCE(l.total_assets_usd, 0) AS total_assets_usd,
        a.first_period,
        a.last_period,
        (a.last_period = '{latest_period}') AS is_active
    FROM agg a
    LEFT JOIN latest l ON a.ruc = l.ruc
    LEFT JOIN dim_provinces p ON a.province_code = p.code;
    """)

    print("[4/6] Calculando componentes derivados por entidad y periodo...")
    con.execute("""
    CREATE TABLE monthly_components AS
    WITH base AS (
        SELECT 
            b.*,
            MONTH(b.fecha) AS mes,
            YEAR(b.fecha) AS anio,
            (b.c14 - b.c1499) AS cartera_bruta,
            -b.c1499 AS provision_cartera,
            (b.c5 - b.c4) AS resultado_ejercicio_ytd,
            (COALESCE(b.c3603, 0) + COALESCE(b.c3604, 0)) AS resultado_cierre,
            (b.cartera_improductiva + b.c1499 - COALESCE(b.c1901, 0) + COALESCE(b.c16, 0) + COALESCE(b.c17, 0) + COALESCE(b.c18, 0) + COALESCE(b.c19, 0)) AS act_inmo_net,
            (b.c51 - b.c41 + b.c52 + b.c54 - b.c42 + b.c53 - b.c43 - b.c44) AS marg_fin_neto,
            ((b.c51 - b.c41 + b.c52 + b.c54 - b.c42 + b.c53 - b.c43 - b.c44 - b.c45) * 12.0 / mes) AS marg_inter_est_annual,
            (b.c4501 * 12.0 / mes) AS c4501_annual,
            (b.c5104 * 12.0 / mes) AS c5104_annual,
            (b.impr_comer_pri + b.impr_comer_ord + b.impr_prod) AS impr_comercial,
            (b.bruta_comer_pri + b.bruta_comer_ord + b.bruta_prod) AS bruta_comercial,
            (b.impr_inmob + b.impr_viv_pub) AS impr_vivienda,
            (b.bruta_inmob + b.bruta_viv_pub) AS bruta_vivienda,
            (b.prov_prod + b.prov_prod_esp + b.prov_comer_ord) AS prov_comercial,
            (b.prov_consu + b.prov_consu_ord) AS prov_consumo,
            (b.prov_inmob + b.prov_viv_pub) AS prov_vivienda,
            (b.xvenc_consu_pri + b.xvenc_consu_ord) AS xvenc_consu_total
        FROM raw_balances b
    ),
    with_ytd AS (
        SELECT 
            b.*,
            AVG(b.c1) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS activo_promedio_ytd,
            AVG(b.c3) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS patrimonio_promedio_ytd,
            AVG(b.cartera_x_vencer) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cartera_vencer_promedio_ytd,
            AVG(b.xvenc_comer_pri) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_comer_pri_ytd,
            AVG(b.xvenc_consu_pri) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_consu_pri_ytd,
            AVG(b.xvenc_consu_total) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_consu_total_ytd,
            AVG(b.xvenc_inmob) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_inmob_ytd,
            AVG(b.xvenc_micro) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_micro_ytd,
            AVG(b.xvenc_prod) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_prod_ytd,
            AVG(b.xvenc_comer_ord) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_comer_ord_ytd,
            AVG(b.xvenc_consu_ord) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_consu_ord_ytd,
            AVG(b.xvenc_viv_pub) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_viv_pub_ytd,
            AVG(b.xvenc_educ) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_educ_ytd,
            AVG(b.xvenc_refi) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_refi_ytd,
            AVG(b.xvenc_rest) OVER (PARTITION BY b.ruc, b.anio ORDER BY b.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS xvenc_rest_ytd
        FROM base b
    )
    SELECT * FROM with_ytd;
    """)

    print("[5/6] Generando tabla de hechos de 63 indicadores para todas las entidades...")
    
    con.execute("""
    CREATE TABLE fct_indicators_entity_monthly AS
    -- Ficha 1: Solvencia Patrimonial (Suficiencia)
    SELECT period, ruc, segment, province_code, 'solvencia_patrimonial' AS indicator_id,
        CASE WHEN act_inmo_net > 0 THEN ROUND(((c3 + resultado_ejercicio_ytd) / act_inmo_net) * 100, 4) ELSE NULL END AS value,
        ROUND(c3 + resultado_ejercicio_ytd, 2) AS numerator, ROUND(act_inmo_net, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 2: Proporción de Activos Improductivos Netos
    SELECT period, ruc, segment, province_code, 'seps_2_proporcion_de_activos_improductiv' AS indicator_id,
        CASE WHEN c1 > 0 THEN ROUND((act_inmo_net / c1) * 100, 4) ELSE NULL END AS value,
        ROUND(act_inmo_net, 2) AS numerator, ROUND(c1, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 3: Proporción de Activos Productivos
    SELECT period, ruc, segment, province_code, 'seps_3_proporcion_de_activos_productivos' AS indicator_id,
        CASE WHEN c1 > 0 THEN ROUND(((c1 - act_inmo_net) / c1) * 100, 4) ELSE NULL END AS value,
        ROUND(c1 - act_inmo_net, 2) AS numerator, ROUND(c1, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 4: Utilización del Pasivo con Costo
    SELECT period, ruc, segment, province_code, 'seps_4_utilizaci_n_del_pasivo_con_costo_' AS indicator_id,
        CASE WHEN c1 > 0 THEN ROUND((pasivo_con_costo / c1) * 100, 4) ELSE NULL END AS value,
        ROUND(pasivo_con_costo, 2) AS numerator, ROUND(c1, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 5: Morosidad Cartera Total
    SELECT period, ruc, segment, province_code, 'morosidad_cartera_total' AS indicator_id,
        CASE WHEN cartera_bruta > 0 THEN ROUND((cartera_improductiva / cartera_bruta) * 100, 4) ELSE NULL END AS value,
        ROUND(cartera_improductiva, 2) AS numerator, ROUND(cartera_bruta, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 6: Morosidad Cartera Comercial Prioritario
    SELECT period, ruc, segment, province_code, 'seps_6_morosidad_de_cartera_comercial_pr' AS indicator_id,
        CASE WHEN bruta_comer_pri > 0 THEN ROUND((impr_comer_pri / bruta_comer_pri) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_comer_pri, 2) AS numerator, ROUND(bruta_comer_pri, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 7: Morosidad Cartera Consumo Prioritario
    SELECT period, ruc, segment, province_code, 'seps_7_morosidad_de_cartera_de_consumo_p' AS indicator_id,
        CASE WHEN bruta_consu_pri > 0 THEN ROUND((impr_consu_pri / bruta_consu_pri) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_consu_pri, 2) AS numerator, ROUND(bruta_consu_pri, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 8: Morosidad Cartera Inmobiliaria
    SELECT period, ruc, segment, province_code, 'seps_8_morosidad_de_cartera_inmobiliaria' AS indicator_id,
        CASE WHEN bruta_inmob > 0 THEN ROUND((impr_inmob / bruta_inmob) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_inmob, 2) AS numerator, ROUND(bruta_inmob, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 9: Morosidad de Microcrédito
    SELECT period, ruc, segment, province_code, 'seps_9_morosidad_de_microcredito' AS indicator_id,
        CASE WHEN bruta_micro > 0 THEN ROUND((impr_micro / bruta_micro) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_micro, 2) AS numerator, ROUND(bruta_micro, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 10: Morosidad Cartera Productiva
    SELECT period, ruc, segment, province_code, 'seps_10_morosidad_de_cartera_productiva' AS indicator_id,
        CASE WHEN bruta_prod > 0 THEN ROUND((impr_prod / bruta_prod) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_prod, 2) AS numerator, ROUND(bruta_prod, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 11: Morosidad Cartera Comercial Ordinario
    SELECT period, ruc, segment, province_code, 'seps_11_morosidad_de_cartera_comercial_o' AS indicator_id,
        CASE WHEN bruta_comer_ord > 0 THEN ROUND((impr_comer_ord / bruta_comer_ord) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_comer_ord, 2) AS numerator, ROUND(bruta_comer_ord, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 12: Morosidad Cartera Consumo Ordinario
    SELECT period, ruc, segment, province_code, 'seps_12_morosidad_de_cartera_de_consumo_' AS indicator_id,
        CASE WHEN bruta_consu_ord > 0 THEN ROUND((impr_consu_ord / bruta_consu_ord) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_consu_ord, 2) AS numerator, ROUND(bruta_consu_ord, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 13: Morosidad Cartera Vivienda Interés Público
    SELECT period, ruc, segment, province_code, 'seps_13_morosidad_de_cartera_de_vivienda' AS indicator_id,
        CASE WHEN bruta_viv_pub > 0 THEN ROUND((impr_viv_pub / bruta_viv_pub) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_viv_pub, 2) AS numerator, ROUND(bruta_viv_pub, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 14: Morosidad Cartera Educativa
    SELECT period, ruc, segment, province_code, 'seps_14_morosidad_de_cartera_educativa' AS indicator_id,
        CASE WHEN bruta_educ > 0 THEN ROUND((impr_educ / bruta_educ) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_educ, 2) AS numerator, ROUND(bruta_educ, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 15: Morosidad Cartera Comercial Total
    SELECT period, ruc, segment, province_code, 'seps_15_morosidad_de_cartera_comercial' AS indicator_id,
        CASE WHEN bruta_comercial > 0 THEN ROUND((impr_comercial / bruta_comercial) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_comercial, 2) AS numerator, ROUND(bruta_comercial, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 16: Morosidad Cartera Consumo Total
    SELECT period, ruc, segment, province_code, 'seps_16_morosidad_de_cartera_de_consumo' AS indicator_id,
        CASE WHEN bruta_consu > 0 THEN ROUND((impr_consu / bruta_consu) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_consu, 2) AS numerator, ROUND(bruta_consu, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 17: Morosidad Cartera Vivienda Total
    SELECT period, ruc, segment, province_code, 'seps_17_morosidad_de_cartera_de_vivienda' AS indicator_id,
        CASE WHEN bruta_vivienda > 0 THEN ROUND((impr_vivienda / bruta_vivienda) * 100, 4) ELSE NULL END AS value,
        ROUND(impr_vivienda, 2) AS numerator, ROUND(bruta_vivienda, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 18: Cobertura Cartera Improductiva Total
    SELECT period, ruc, segment, province_code, 'cobertura_cartera_improductiva' AS indicator_id,
        CASE WHEN cartera_improductiva > 0 THEN ROUND((provision_cartera / cartera_improductiva) * 100, 4) ELSE NULL END AS value,
        ROUND(provision_cartera, 2) AS numerator, ROUND(cartera_improductiva, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 19: Cobertura Cartera Comercial Prioritario
    SELECT period, ruc, segment, province_code, 'seps_19_cobertura_de_la_cartera_de_cr_di' AS indicator_id,
        CASE WHEN impr_comer_pri > 0 THEN ROUND((prov_prod / impr_comer_pri) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_prod, 2) AS numerator, ROUND(impr_comer_pri, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 20: Cobertura Cartera Consumo Prioritario
    SELECT period, ruc, segment, province_code, 'seps_20_cobertura_de_la_cartera_de_cr_di' AS indicator_id,
        CASE WHEN impr_consu_pri > 0 THEN ROUND((prov_consu / impr_consu_pri) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_consu, 2) AS numerator, ROUND(impr_consu_pri, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 21: Cobertura Cartera Inmobiliaria
    SELECT period, ruc, segment, province_code, 'seps_21_cobertura_de_la_cartera_inmobili' AS indicator_id,
        CASE WHEN impr_inmob > 0 THEN ROUND((prov_inmob / impr_inmob) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_inmob, 2) AS numerator, ROUND(impr_inmob, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 22: Cobertura Cartera Microcrédito
    SELECT period, ruc, segment, province_code, 'seps_22_cobertura_de_la_cartera_de_micro' AS indicator_id,
        CASE WHEN impr_micro > 0 THEN ROUND((prov_micro / impr_micro) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_micro, 2) AS numerator, ROUND(impr_micro, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 23: Cobertura Cartera Productiva
    SELECT period, ruc, segment, province_code, 'seps_23_cobertura_de_la_cartera_producti' AS indicator_id,
        CASE WHEN impr_prod > 0 THEN ROUND((prov_prod_esp / impr_prod) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_prod_esp, 2) AS numerator, ROUND(impr_prod, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 24: Cobertura Cartera Comercial Ordinario
    SELECT period, ruc, segment, province_code, 'seps_24_cobertura_de_la_cartera_comercia' AS indicator_id,
        CASE WHEN impr_comer_ord > 0 THEN ROUND((prov_comer_ord / impr_comer_ord) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_comer_ord, 2) AS numerator, ROUND(impr_comer_ord, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 25: Cobertura Cartera Consumo Ordinario
    SELECT period, ruc, segment, province_code, 'seps_25_cobertura_de_la_cartera_de_consu' AS indicator_id,
        CASE WHEN impr_consu_ord > 0 THEN ROUND((prov_consu_ord / impr_consu_ord) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_consu_ord, 2) AS numerator, ROUND(impr_consu_ord, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 26: Cobertura Cartera Vivienda Interés Público
    SELECT period, ruc, segment, province_code, 'seps_26_cobertura_de_la_cartera_de_vivie' AS indicator_id,
        CASE WHEN impr_viv_pub > 0 THEN ROUND((prov_viv_pub / impr_viv_pub) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_viv_pub, 2) AS numerator, ROUND(impr_viv_pub, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 27: Cobertura Cartera Crédito Educativo
    SELECT period, ruc, segment, province_code, 'seps_27_cobertura_de_la_cartera_de_cr_di' AS indicator_id,
        CASE WHEN impr_educ > 0 THEN ROUND((prov_educ / impr_educ) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_educ, 2) AS numerator, ROUND(impr_educ, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 28: Cobertura Cartera Comercial Total
    SELECT period, ruc, segment, province_code, 'seps_28_cobertura_de_la_cartera_comercia' AS indicator_id,
        CASE WHEN impr_comercial > 0 THEN ROUND((prov_comercial / impr_comercial) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_comercial, 2) AS numerator, ROUND(impr_comercial, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 29: Cobertura Cartera Consumo Total
    SELECT period, ruc, segment, province_code, 'seps_29_cobertura_de_la_cartera_de_consu' AS indicator_id,
        CASE WHEN impr_consu > 0 THEN ROUND((prov_consumo / impr_consu) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_consumo, 2) AS numerator, ROUND(impr_consu, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 30: Cobertura Cartera Vivienda Total
    SELECT period, ruc, segment, province_code, 'seps_30_cobertura_de_la_cartera_de_vivie' AS indicator_id,
        CASE WHEN impr_vivienda > 0 THEN ROUND((prov_vivienda / impr_vivienda) * 100, 4) ELSE NULL END AS value,
        ROUND(prov_vivienda, 2) AS numerator, ROUND(impr_vivienda, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 31: Eficiencia Operativa
    SELECT period, ruc, segment, province_code, 'eficiencia_operativa' AS indicator_id,
        CASE WHEN ROUND(activo_promedio_ytd, 2) > 0 THEN ROUND((ROUND(c45 * 12.0 / mes, 2) / ROUND(activo_promedio_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c45 * 12.0 / mes, 2) AS numerator, ROUND(activo_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 32: Grado de Absorción del Margen Financiero
    SELECT period, ruc, segment, province_code, 'seps_32_grado_de_absorci_n_del_margen_fi' AS indicator_id,
        CASE WHEN ROUND(marg_fin_neto, 2) > 0 THEN ROUND((ROUND(c45 * 12.0 / mes, 2) / ROUND(marg_fin_neto, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c45 * 12.0 / mes, 2) AS numerator, ROUND(marg_fin_neto, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 33: Eficiencia Administrativa de Personal
    SELECT period, ruc, segment, province_code, 'seps_33_eficiencia_administrativa_de_per' AS indicator_id,
        CASE WHEN ROUND(activo_promedio_ytd, 2) > 0 THEN ROUND((ROUND(c4501_annual, 2) / ROUND(activo_promedio_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c4501_annual, 2) AS numerator, ROUND(activo_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 34: ROE (Homogeneizado con patrimonio promedio YTD de 12 meses)
    SELECT period, ruc, segment, province_code, 'roe' AS indicator_id,
        CASE 
            WHEN mes = 12 AND ROUND(patrimonio_promedio_ytd, 2) > 0 THEN ROUND((ROUND(resultado_cierre, 2) / ROUND(patrimonio_promedio_ytd, 2)) * 100, 4)
            WHEN mes < 12 AND ROUND(patrimonio_promedio_ytd, 2) > 0 THEN ROUND((ROUND(resultado_ejercicio_ytd * 12.0 / mes, 2) / ROUND(patrimonio_promedio_ytd, 2)) * 100, 4)
            ELSE NULL 
        END AS value,
        ROUND(CASE WHEN mes = 12 THEN resultado_cierre ELSE (resultado_ejercicio_ytd * 12.0 / mes) END, 2) AS numerator,
        ROUND(patrimonio_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 35: ROA (Homogeneizado con activo promedio YTD de 12 meses)
    SELECT period, ruc, segment, province_code, 'roa' AS indicator_id,
        CASE 
            WHEN mes = 12 AND ROUND(activo_promedio_ytd, 2) > 0 THEN ROUND((ROUND(resultado_cierre, 2) / ROUND(activo_promedio_ytd, 2)) * 100, 4)
            WHEN mes < 12 AND ROUND(activo_promedio_ytd, 2) > 0 THEN ROUND((ROUND(resultado_ejercicio_ytd * 12.0 / mes, 2) / ROUND(activo_promedio_ytd, 2)) * 100, 4)
            ELSE NULL 
        END AS value,
        ROUND(CASE WHEN mes = 12 THEN resultado_cierre ELSE (resultado_ejercicio_ytd * 12.0 / mes) END, 2) AS numerator,
        ROUND(activo_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 36: Intermediación Financiera
    SELECT period, ruc, segment, province_code, 'intermediacion_financiera' AS indicator_id,
        CASE WHEN ROUND(c21, 2) > 0 THEN ROUND((ROUND(cartera_bruta, 2) / ROUND(c21, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(cartera_bruta, 2) AS numerator, ROUND(c21, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 37: Margen de Intermediación Estimado sobre Patrimonio Promedio
    SELECT period, ruc, segment, province_code, 'seps_37_margen_de_intermediaci_n_estimad' AS indicator_id,
        CASE WHEN ROUND(patrimonio_promedio_ytd, 2) > 0 THEN ROUND((ROUND(marg_inter_est_annual, 2) / ROUND(patrimonio_promedio_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(marg_inter_est_annual, 2) AS numerator, ROUND(patrimonio_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 38: Margen de Intermediación Estimado sobre Activo Promedio
    SELECT period, ruc, segment, province_code, 'seps_38_margen_de_intermediaci_n_estimad' AS indicator_id,
        CASE WHEN ROUND(activo_promedio_ytd, 2) > 0 THEN ROUND((ROUND(marg_inter_est_annual, 2) / ROUND(activo_promedio_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(marg_inter_est_annual, 2) AS numerator, ROUND(activo_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 39: Rendimiento Cartera Comercial Prioritario por Vencer
    SELECT period, ruc, segment, province_code, 'seps_39_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_comer_pri_ytd, 2) > 0 THEN ROUND((ROUND(c510405 * 12.0 / mes, 2) / ROUND(xvenc_comer_pri_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510405 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_comer_pri_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 40: Rendimiento Cartera Consumo Prioritario por Vencer
    SELECT period, ruc, segment, province_code, 'seps_40_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_consu_pri_ytd, 2) > 0 THEN ROUND((ROUND(c510410 * 12.0 / mes, 2) / ROUND(xvenc_consu_pri_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510410 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_consu_pri_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 41: Rendimiento Cartera Consumo Total por Vencer
    SELECT period, ruc, segment, province_code, 'seps_41_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_consu_total_ytd, 2) > 0 THEN ROUND((ROUND(c510410 * 12.0 / mes, 2) / ROUND(xvenc_consu_total_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510410 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_consu_total_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 42: Rendimiento Cartera Inmobiliario por Vencer
    SELECT period, ruc, segment, province_code, 'seps_42_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_inmob_ytd, 2) > 0 THEN ROUND((ROUND(c510415 * 12.0 / mes, 2) / ROUND(xvenc_inmob_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510415 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_inmob_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 43: Rendimiento Cartera Microcrédito por Vencer
    SELECT period, ruc, segment, province_code, 'seps_43_rendimiento_de_la_cartera_de_mic' AS indicator_id,
        CASE WHEN ROUND(xvenc_micro_ytd, 2) > 0 THEN ROUND((ROUND(c510420 * 12.0 / mes, 2) / ROUND(xvenc_micro_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510420 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_micro_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 44: Rendimiento Cartera Productivo por Vencer
    SELECT period, ruc, segment, province_code, 'seps_44_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_prod_ytd, 2) > 0 THEN ROUND((ROUND(c510421 * 12.0 / mes, 2) / ROUND(xvenc_prod_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510421 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_prod_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 45: Rendimiento Cartera Comercial Ordinario por Vencer
    SELECT period, ruc, segment, province_code, 'seps_45_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_comer_ord_ytd, 2) > 0 THEN ROUND((ROUND(c510425 * 12.0 / mes, 2) / ROUND(xvenc_comer_ord_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510425 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_comer_ord_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 46: Rendimiento Cartera Consumo Ordinario por Vencer
    SELECT period, ruc, segment, province_code, 'seps_46_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_consu_ord_ytd, 2) > 0 THEN ROUND((ROUND(c510426 * 12.0 / mes, 2) / ROUND(xvenc_consu_ord_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510426 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_consu_ord_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 47: Rendimiento Cartera Vivienda Interés Público por Vencer
    SELECT period, ruc, segment, province_code, 'seps_47_rendimiento_de_la_cartera_de_viv' AS indicator_id,
        CASE WHEN ROUND(xvenc_viv_pub_ytd, 2) > 0 THEN ROUND((ROUND(c510427 * 12.0 / mes, 2) / ROUND(xvenc_viv_pub_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510427 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_viv_pub_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 48: Rendimiento Cartera Educativo por Vencer
    SELECT period, ruc, segment, province_code, 'seps_48_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_educ_ytd, 2) > 0 THEN ROUND((ROUND(c510428 * 12.0 / mes, 2) / ROUND(xvenc_educ_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510428 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_educ_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 49: Rendimiento Cartera Refinanciada por Vencer
    SELECT period, ruc, segment, province_code, 'seps_49_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_refi_ytd, 2) > 0 THEN ROUND((ROUND(c510430 * 12.0 / mes, 2) / ROUND(xvenc_refi_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510430 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_refi_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 50: Rendimiento Cartera Reestructurada por Vencer
    SELECT period, ruc, segment, province_code, 'seps_50_rendimiento_de_la_cartera_de_cr_' AS indicator_id,
        CASE WHEN ROUND(xvenc_rest_ytd, 2) > 0 THEN ROUND((ROUND(c510435 * 12.0 / mes, 2) / ROUND(xvenc_rest_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c510435 * 12.0 / mes, 2) AS numerator, ROUND(xvenc_rest_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 51: Rendimiento de la Cartera por Vencer Total
    SELECT period, ruc, segment, province_code, 'seps_51_rendimiento_de_la_cartera_por_ve' AS indicator_id,
        CASE WHEN ROUND(cartera_vencer_promedio_ytd, 2) > 0 THEN ROUND((ROUND(c5104_annual, 2) / ROUND(cartera_vencer_promedio_ytd, 2)) * 100, 4) ELSE NULL END AS value,
        ROUND(c5104_annual, 2) AS numerator, ROUND(cartera_vencer_promedio_ytd, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 52: Liquidez Inmediata (AUD-07: Fondos Disponibles / Depósitos a Corto Plazo)
    SELECT period, ruc, segment, province_code, 'liquidez_inmediata' AS indicator_id,
        CASE WHEN depo_corto_plazo > 0 THEN ROUND((c11 / depo_corto_plazo) * 100, 4) ELSE NULL END AS value,
        ROUND(c11, 2) AS numerator, ROUND(depo_corto_plazo, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 53: Cartera Improductiva Descubierta sobre Activos
    SELECT period, ruc, segment, province_code, 'seps_53_cartera_improductiva_descubierta' AS indicator_id,
        CASE WHEN c1 > 0 THEN ROUND(((cartera_improductiva - provision_cartera) / c1) * 100, 4) ELSE NULL END AS value,
        ROUND(cartera_improductiva - provision_cartera, 2) AS numerator, ROUND(c1, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 54: Cartera Improductiva sobre Patrimonio
    SELECT period, ruc, segment, province_code, 'seps_54_cartera_improductiva_sobre_el_pa' AS indicator_id,
        CASE WHEN c3 > 0 THEN ROUND((cartera_improductiva / c3) * 100, 4) ELSE NULL END AS value,
        ROUND(cartera_improductiva, 2) AS numerator, ROUND(c3, 2) AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 55: FK = Patrimonio + Resultados - Ingresos No Operacionales
    SELECT period, ruc, segment, province_code, 'seps_55_fk_patrimonio_resultados_ingreso' AS indicator_id,
        ROUND(c3 + (c5 - c4) - c56, 2) AS value,
        ROUND(c3 + (c5 - c4) - c56, 2) AS numerator,
        NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 56: FI = 1 + (Activos Improductivos / Activos Totales)
    SELECT period, ruc, segment, province_code, 'seps_56_fi_1_activos_improductivos_activ' AS indicator_id,
        CASE WHEN c1 > 0 THEN ROUND(1.0 + (act_inmo_net / c1), 4) ELSE NULL END AS value,
        ROUND(act_inmo_net, 2) AS numerator,
        NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 57: Indice de Capitalización Neto (FK / FI)
    SELECT period, ruc, segment, province_code, 'seps_57_indice_de_capitalizaci_n_neto_fk' AS indicator_id,
        CASE WHEN (1.0 + (act_inmo_net / NULLIF(c1, 0))) > 0 THEN ROUND((c3 + (c5 - c4) - c56) / (1.0 + (act_inmo_net / c1)), 2) ELSE NULL END AS value,
        ROUND(c3 + (c5 - c4) - c56, 2) AS numerator,
        NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM monthly_components
    UNION ALL
    -- Ficha 58: Patrimonio Técnico Primario (PTP)
    SELECT period, ruc, segment, province_code, 'seps_58_patrimonio_t_cnico_primario' AS indicator_id,
        ROUND(ptp, 2) AS value, ROUND(ptp, 2) AS numerator, NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE ptp IS NOT NULL
    UNION ALL
    -- Ficha 59: Patrimonio Técnico Secundario (PTS)
    SELECT period, ruc, segment, province_code, 'seps_59_patrimonio_t_cnico_secundario' AS indicator_id,
        ROUND(pts, 2) AS value, ROUND(pts, 2) AS numerator, NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE pts IS NOT NULL
    UNION ALL
    -- Ficha 60: Patrimonio Técnico Constituido (PTC)
    SELECT period, ruc, segment, province_code, 'seps_60_patrimonio_t_cnico_constituido' AS indicator_id,
        ROUND(ptc, 2) AS value, ROUND(ptc, 2) AS numerator, NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE ptc IS NOT NULL
    UNION ALL
    -- Ficha 61: Activos y Contingentes Ponderados por Riesgo (APR)
    SELECT period, ruc, segment, province_code, 'seps_61_activos_y_contingentes_ponderado' AS indicator_id,
        ROUND(apr, 2) AS value, ROUND(apr, 2) AS numerator, NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE apr IS NOT NULL
    UNION ALL
    -- Ficha 62: Solvencia Legal (COMF Art. 190)
    SELECT period, ruc, segment, province_code, 'seps_62_solvencia' AS indicator_id,
        solvencia AS value, ROUND(ptc, 2) AS numerator, ROUND(apr, 2) AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE ptc IS NOT NULL AND apr > 0
    UNION ALL
    -- Ficha 63: Porcentaje Técnico Requerido (PTR = ACPR * PMS, PMS=9%)
    SELECT period, ruc, segment, province_code, 'seps_63_porcentaje_t_cnico_requerido' AS indicator_id,
        ROUND(apr * 0.09, 2) AS value, ROUND(apr * 0.09, 2) AS numerator, NULL::DOUBLE AS denominator, 1 AS entity_count
    FROM read_parquet('data/interim/patrimonio_tecnico/patrimonio_tecnico_monthly.parquet')
    WHERE apr IS NOT NULL;
    """)

    # Hechos Segmento (Ratio de Sumas y Agregación de Volúmenes)
    con.execute("""
    CREATE TABLE fct_indicators_segment_monthly AS
    SELECT 
        period, segment, indicator_id,
        CASE 
            WHEN indicator_id IN (
                'seps_58_patrimonio_t_cnico_primario',
                'seps_59_patrimonio_t_cnico_secundario',
                'seps_60_patrimonio_t_cnico_constituido',
                'seps_61_activos_y_contingentes_ponderado',
                'seps_63_porcentaje_t_cnico_requerido',
                'seps_55_fk_patrimonio_resultados_ingreso',
                'seps_57_indice_de_capitalizaci_n_neto_fk'
            ) THEN ROUND(SUM(numerator), 2)
            WHEN indicator_id = 'seps_56_fi_1_activos_improductivos_activ' THEN ROUND(AVG(value), 4)
            WHEN SUM(denominator) > 0 THEN ROUND((SUM(numerator) / SUM(denominator)) * 100, 4)
            ELSE NULL 
        END AS value,
        ROUND(SUM(numerator), 2) AS numerator,
        ROUND(SUM(denominator), 2) AS denominator,
        COUNT(DISTINCT ruc) AS entity_count
    FROM fct_indicators_entity_monthly
    GROUP BY period, segment, indicator_id;
    """)

    # Hechos País (Consolidado nacional de todas las cooperativas)
    con.execute("""
    CREATE TABLE fct_indicators_country_monthly AS
    SELECT 
        period, indicator_id,
        CASE 
            WHEN indicator_id IN (
                'seps_58_patrimonio_t_cnico_primario',
                'seps_59_patrimonio_t_cnico_secundario',
                'seps_60_patrimonio_t_cnico_constituido',
                'seps_61_activos_y_contingentes_ponderado',
                'seps_63_porcentaje_t_cnico_requerido',
                'seps_55_fk_patrimonio_resultados_ingreso',
                'seps_57_indice_de_capitalizaci_n_neto_fk'
            ) THEN ROUND(SUM(numerator), 2)
            WHEN indicator_id = 'seps_56_fi_1_activos_improductivos_activ' THEN ROUND(AVG(value), 4)
            WHEN SUM(denominator) > 0 THEN ROUND((SUM(numerator) / SUM(denominator)) * 100, 4)
            ELSE NULL 
        END AS value,
        ROUND(SUM(numerator), 2) AS numerator,
        ROUND(SUM(denominator), 2) AS denominator,
        COUNT(DISTINCT ruc) AS entity_count
    FROM fct_indicators_entity_monthly
    GROUP BY period, indicator_id;
    """)

    print("[6/6] Guardando data marts en formato Parquet...")
    
    con.execute(f"COPY dim_provinces TO '{out_dir / 'dim_provinces.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    con.execute(f"COPY dim_segments TO '{out_dir / 'dim_segments.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    con.execute(f"COPY dim_entities TO '{out_dir / 'dim_entities.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    con.execute(f"COPY fct_indicators_entity_monthly TO '{out_dir / 'fct_indicators_entity_monthly.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    con.execute(f"COPY fct_indicators_segment_monthly TO '{out_dir / 'fct_indicators_segment_monthly.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")
    con.execute(f"COPY fct_indicators_country_monthly TO '{out_dir / 'fct_indicators_country_monthly.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD);")

    # AUD-10: Particionamiento Hive en Parquet para optimizar consultas de series analíticas
    partition_dir = out_dir / "partitioned" / "fct_indicators_entity"
    partition_dir.mkdir(parents=True, exist_ok=True)
    partition_path = str(partition_dir).replace("\\", "/")
    print(f"Exportando hechos particionados (Hive partitioning) a {partition_path}...")
    con.execute(f"""
        COPY (
            SELECT *, SUBSTRING(period, 1, 4) AS year 
            FROM fct_indicators_entity_monthly
        ) TO '{partition_path}' (FORMAT PARQUET, PARTITION_BY (indicator_id, year), COMPRESSION ZSTD, OVERWRITE_OR_IGNORE 1);
    """)

    n_entities = con.execute("SELECT COUNT(*) FROM dim_entities;").fetchone()[0]
    n_fct = con.execute("SELECT COUNT(*) FROM fct_indicators_entity_monthly;").fetchone()[0]
    n_indicators = con.execute("SELECT COUNT(DISTINCT indicator_id) FROM fct_indicators_entity_monthly;").fetchone()[0]
    print(f"Data Marts construidos exitosamente.")
    print(f"Total entidades registradas: {n_entities}")
    print(f"Total indicadores únicos generados: {n_indicators} / 63")
    print(f"Total registros en hechos mensuales: {n_fct:,}")

if __name__ == "__main__":
    build_marts()
