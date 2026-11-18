import test from "node:test"
import assert from "node:assert/strict"
import {
  computeSegmentCounts,
  computeProvinceOptions,
  resolveProvinceSegmentFilter,
  resolveSegmentProvinceFilter,
  resolveEffectiveChartIndicator,
  buildChartSeriesData,
  buildBarComparisonData,
  formatSegmentFilterLabel,
  resolveNeutralTrafficLightLabel
} from "./benchmarkingModel"
import type {
  BenchmarkingCompareResponse,
  BenchmarkingIndicatorRow,
  EntitySummary
} from "../services/httpClient"

const SAMPLE_ENTITIES: EntitySummary[] = [
  {
    ruc: "0190155722001",
    razon_social: "COOPERATIVA DE AHORRO Y CREDITO JARDIN AZUAYO LIMITADA",
    segment: "SEGMENTO_1",
    province: { code: "01", name: "AZUAY" },
    total_assets_usd: 1500000000
  },
  {
    ruc: "0690000000001",
    razon_social: "COOPERATIVA RIOBAMBA LTDA",
    segment: "SEGMENTO_2",
    province: { code: "06", name: "CHIMBORAZO" },
    total_assets_usd: 45000000
  },
  {
    ruc: "1790000000001",
    razon_social: "COOPERATIVA PICHINCHA LTDA",
    segment: "SEGMENTO_1",
    province: { code: "17", name: "PICHINCHA" },
    total_assets_usd: 900000000
  }
] as EntitySummary[]

test("computeSegmentCounts filters by province and totals correctly", () => {
  const all = computeSegmentCounts(SAMPLE_ENTITIES, "all")
  assert.equal(all.all, 3)
  assert.equal(all.SEGMENTO_1, 2)
  assert.equal(all.SEGMENTO_2, 1)

  const chimborazo = computeSegmentCounts(SAMPLE_ENTITIES, "CHIMBORAZO")
  assert.equal(chimborazo.all, 1)
  assert.equal(chimborazo.SEGMENTO_1, 0)
  assert.equal(chimborazo.SEGMENTO_2, 1)
})

test("bidirectional province <-> segment filter resets incompatible axis to all", () => {
  const res1 = resolveProvinceSegmentFilter(SAMPLE_ENTITIES, "CHIMBORAZO", "SEGMENTO_1")
  assert.deepEqual(res1, { province: "CHIMBORAZO", segment: "all" })

  const res2 = resolveSegmentProvinceFilter(SAMPLE_ENTITIES, "SEGMENTO_1", "CHIMBORAZO")
  assert.deepEqual(res2, { segment: "SEGMENTO_1", province: "all" })

  const compatible = computeProvinceOptions(SAMPLE_ENTITIES, "SEGMENTO_1")
  assert.deepEqual(compatible.map((p) => p.name), ["AZUAY", "PICHINCHA"])
})

test("resolveEffectiveChartIndicator falls back to first indicator without mutating state", () => {
  const indicators = [
    { indicator_id: "solvencia_patrimonial" },
    { indicator_id: "morosidad_cartera_total" }
  ] as BenchmarkingIndicatorRow[]

  assert.equal(resolveEffectiveChartIndicator(indicators, "morosidad_cartera_total"), "morosidad_cartera_total")
  assert.equal(resolveEffectiveChartIndicator(indicators, "no_existe"), "solvencia_patrimonial")
})

test("buildChartSeriesData and buildBarComparisonData shape series and bars cleanly", () => {
  const indicatorMeta = {
    indicator_id: "solvencia_patrimonial",
    country_baseline: 14.5,
    segment1_baseline: 15.2,
    entity_values: { "0190155722001": 16.8 }
  } as unknown as BenchmarkingIndicatorRow

  const benchmarkData = {
    entities: [SAMPLE_ENTITIES[0]],
    indicators: [indicatorMeta],
    time_series: {
      solvencia_patrimonial: [
        { period: "2025-10", segment1_baseline: 15.0, country_baseline: 14.0, entity_values: { "0190155722001": 16.0 } },
        { period: "2025-11", segment1_baseline: 15.1, country_baseline: 14.2, entity_values: { "0190155722001": 16.4 } },
        { period: "2025-12", segment1_baseline: 15.2, country_baseline: 14.5, entity_values: { "0190155722001": 16.8 } }
      ]
    }
  } as unknown as BenchmarkingCompareResponse

  const series = buildChartSeriesData(benchmarkData, "solvencia_patrimonial", 2)
  assert.equal(series.length, 2)
  assert.equal(series[0].period, "2025-11")
  assert.equal(series[1]["0190155722001"], 16.8)

  const bars = buildBarComparisonData(indicatorMeta, benchmarkData)
  assert.equal(bars.length, 3)
  assert.equal(bars[0].name, "Media Nacional")
  assert.equal(bars[2].value, 16.8)
})

test("formatSegmentFilterLabel exposes Trimestral badge only for quarterly segments", () => {
  assert.deepEqual(
    formatSegmentFilterLabel({ label: "Segmento 1", reporting_frequency: "monthly" }),
    { shortLabel: "Seg 1", frequencyBadge: null }
  )
  assert.deepEqual(
    formatSegmentFilterLabel({ label: "Segmento 4", reporting_frequency: "quarterly" }),
    { shortLabel: "Seg 4", frequencyBadge: "Trimestral" }
  )
})

test("resolveNeutralTrafficLightLabel returns Sin dato for null indicator values", () => {
  assert.equal(resolveNeutralTrafficLightLabel(null), "Sin dato")
  assert.equal(resolveNeutralTrafficLightLabel(undefined), "Sin dato")
  assert.equal(resolveNeutralTrafficLightLabel(12.5), null)
})
