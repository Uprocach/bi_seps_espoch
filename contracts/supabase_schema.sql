-- =============================================================================
-- SISTEMA DE INDICADORES FINANCIEROS SFPS (SEPS)
-- Esquema de Producción para Supabase (PostgreSQL 15+)
-- Spec-Driven Development: Alineado con contracts/openapi.yaml
-- =============================================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- -----------------------------------------------------------------------------
-- 1. TABLA: dim_provinces (Catálogo oficial DPA INEC)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_provinces (
    code CHAR(2) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 2. TABLA: dim_segments (Segmentos normativos de la SEPS)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_segments (
    code VARCHAR(50) PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    reporting_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- 3. TABLA: dim_entities (Directorio de Cooperativas y Mutualistas)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_entities (
    ruc CHAR(13) PRIMARY KEY,
    razon_social VARCHAR(255) NOT NULL,
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('COOPERATIVA', 'MUTUALISTA', 'CAJA_CENTRAL')),
    segment VARCHAR(50) NOT NULL REFERENCES dim_segments(code),
    province_code CHAR(2) NOT NULL REFERENCES dim_provinces(code),
    total_assets_usd NUMERIC(18, 2),
    first_period CHAR(7) NOT NULL, -- Formato YYYY-MM
    last_period CHAR(7) NOT NULL,  -- Formato YYYY-MM
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para búsqueda rápida en /api/v1/entities
CREATE INDEX IF NOT EXISTS idx_entities_segment ON dim_entities(segment);
CREATE INDEX IF NOT EXISTS idx_entities_province ON dim_entities(province_code);
CREATE INDEX IF NOT EXISTS idx_entities_assets ON dim_entities(total_assets_usd DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_entities_trgm_search ON dim_entities USING gin (razon_social gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- 4. TABLA: fct_indicators_entity_monthly (Nivel Entidad)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fct_indicators_entity_monthly (
    period CHAR(7) NOT NULL, -- Formato YYYY-MM
    ruc CHAR(13) NOT NULL REFERENCES dim_entities(ruc) ON DELETE CASCADE,
    segment VARCHAR(50) NOT NULL REFERENCES dim_segments(code),
    province_code CHAR(2) NOT NULL REFERENCES dim_provinces(code),
    indicator_id VARCHAR(100) NOT NULL,
    value NUMERIC(12, 4),
    numerator NUMERIC(18, 2),
    denominator NUMERIC(18, 2),
    entity_count INT NOT NULL DEFAULT 1,
    PRIMARY KEY (period, ruc, indicator_id)
);

-- Índices para consultas de series en /api/v1/indicators/series?level=entity
CREATE INDEX IF NOT EXISTS idx_fct_ent_series ON fct_indicators_entity_monthly(indicator_id, ruc, period);
CREATE INDEX IF NOT EXISTS idx_fct_ent_period ON fct_indicators_entity_monthly(period);

-- -----------------------------------------------------------------------------
-- 5. TABLA: fct_indicators_segment_monthly (Pre-agregado Nivel Segmento)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fct_indicators_segment_monthly (
    period CHAR(7) NOT NULL,
    segment VARCHAR(50) NOT NULL REFERENCES dim_segments(code),
    indicator_id VARCHAR(100) NOT NULL,
    value NUMERIC(12, 4),
    numerator NUMERIC(18, 2),
    denominator NUMERIC(18, 2),
    entity_count INT NOT NULL,
    PRIMARY KEY (period, segment, indicator_id)
);

CREATE INDEX IF NOT EXISTS idx_fct_seg_series ON fct_indicators_segment_monthly(indicator_id, segment, period);

-- -----------------------------------------------------------------------------
-- 6. TABLA: fct_indicators_country_monthly (Pre-agregado Nivel País / Sistema)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fct_indicators_country_monthly (
    period CHAR(7) NOT NULL,
    country_code CHAR(2) NOT NULL DEFAULT 'EC',
    indicator_id VARCHAR(100) NOT NULL,
    value NUMERIC(12, 4),
    numerator NUMERIC(18, 2),
    denominator NUMERIC(18, 2),
    entity_count INT NOT NULL,
    PRIMARY KEY (period, indicator_id)
);

CREATE INDEX IF NOT EXISTS idx_fct_cty_series ON fct_indicators_country_monthly(indicator_id, period);

-- -----------------------------------------------------------------------------
-- 7. POLÍTICAS DE SEGURIDAD (Row Level Security - RLS)
-- -----------------------------------------------------------------------------
-- Habilitar RLS para lectura pública / cliente y escritura restringida al servicio ETL
ALTER TABLE dim_provinces ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE fct_indicators_entity_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE fct_indicators_segment_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE fct_indicators_country_monthly ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to dim_provinces" ON dim_provinces FOR SELECT USING (true);
CREATE POLICY "Allow public read access to dim_segments" ON dim_segments FOR SELECT USING (true);
CREATE POLICY "Allow public read access to dim_entities" ON dim_entities FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public read access to fct_indicators_entity" ON fct_indicators_entity_monthly;
-- Sólo usuarios autenticados con rol accredited_investigator acceden a microdatos
CREATE POLICY "Allow accredited users read access to entity facts" 
ON fct_indicators_entity_monthly 
FOR SELECT 
TO authenticated 
USING (auth.jwt() ->> 'role' IN ('researcher', 'auditor', 'admin'));
CREATE POLICY "Allow public read access to fct_indicators_segment" ON fct_indicators_segment_monthly FOR SELECT USING (true);
CREATE POLICY "Allow public read access to fct_indicators_country" ON fct_indicators_country_monthly FOR SELECT USING (true);
