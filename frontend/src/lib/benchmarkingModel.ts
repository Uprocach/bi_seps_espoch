import type {
  BenchmarkingCompareResponse,
  BenchmarkingIndicatorRow,
  EntitySummary
} from "../services/httpClient"
import type { CamelDimension } from "../types/camel"
import { formatCoopName } from "./utils"

export type ProTabId = "ranking" | CamelDimension

export const PRO_TABS: { id: ProTabId; label: string }[] = [
  { id: "ranking", label: "Ranking de COACs" },
  { id: "capital", label: "Capital y Solvencia" },
  { id: "calidad_de_activos", label: "Calidad de Activos" },
  { id: "manejo_administrativo", label: "Manejo Administrativo" },
  { id: "rentabilidad", label: "Rentabilidad" },
  { id: "liquidez", label: "Liquidez" }
]

export const ENTITY_PALETTE = [
  "#0284C7",
  "#7C3AED",
  "#D97706",
  "#0D9488",
  "#4F46E5"
]

export interface SegmentCounts {
  all: number
  SEGMENTO_1: number
  SEGMENTO_2: number
  SEGMENTO_3: number
  SEGMENTO_1_MUTUALISTA: number
}

function matchesProvince(entity: EntitySummary, province: string): boolean {
  if (province === "all") return true
  const target = province.toLowerCase()
  return (
    (entity.province?.name || "").toLowerCase() === target ||
    (entity.province?.code || "").toLowerCase() === target
  )
}

export function computeSegmentCounts(
  entities: EntitySummary[],
  province: string = "all"
): SegmentCounts {
  const pool =
    province === "all"
      ? entities
      : entities.filter((e) => matchesProvince(e, province))

  const counts: SegmentCounts = {
    all: pool.length,
    SEGMENTO_1: 0,
    SEGMENTO_2: 0,
    SEGMENTO_3: 0,
    SEGMENTO_1_MUTUALISTA: 0
  }

  for (const e of pool) {
    if (e.segment === "SEGMENTO_1") counts.SEGMENTO_1++
    else if (e.segment === "SEGMENTO_2") counts.SEGMENTO_2++
    else if (e.segment === "SEGMENTO_3") counts.SEGMENTO_3++
    else if (e.segment === "SEGMENTO_1_MUTUALISTA") counts.SEGMENTO_1_MUTUALISTA++
  }
  return counts
}

export function computeProvinceOptions(
  entities: EntitySummary[],
  segment: string = "all"
): { name: string; count: number }[] {
  const pool =
    segment === "all"
      ? entities
      : entities.filter((e) => e.segment === segment)

  const provMap: Record<string, number> = {}
  for (const e of pool) {
    const pName = e.province?.name || "Sin Provincia"
    provMap[pName] = (provMap[pName] || 0) + 1
  }

  return Object.entries(provMap)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name, "es"))
}

export function resolveProvinceSegmentFilter(
  entities: EntitySummary[],
  nextProvince: string,
  currentSegment: string
): { province: string; segment: string } {
  if (nextProvince === "all" || currentSegment === "all") {
    return { province: nextProvince, segment: currentSegment }
  }
  const hasMatch = entities.some(
    (e) => matchesProvince(e, nextProvince) && e.segment === currentSegment
  )
  return {
    province: nextProvince,
    segment: hasMatch ? currentSegment : "all"
  }
}

export function resolveSegmentProvinceFilter(
  entities: EntitySummary[],
  nextSegment: string,
  currentProvince: string
): { segment: string; province: string } {
  if (nextSegment === "all" || currentProvince === "all") {
    return { segment: nextSegment, province: currentProvince }
  }
  const hasMatch = entities.some(
    (e) => e.segment === nextSegment && matchesProvince(e, currentProvince)
  )
  return {
    segment: nextSegment,
    province: hasMatch ? currentProvince : "all"
  }
}

export function filterAndSortEntities(
  entities: EntitySummary[],
  options: { query: string; segment: string; sort: "assets" | "name" }
): EntitySummary[] {
  const { query, segment, sort } = options
  let list = entities

  if (segment !== "all") {
    list = list.filter((e) => e.segment === segment)
  }

  const q = query.trim().toLowerCase()
  if (q) {
    list = list.filter((e) => {
      const cleanName = formatCoopName(e.razon_social).toLowerCase()
      const legalName = e.razon_social.toLowerCase()
      const ruc = e.ruc.toLowerCase()
      const province = (e.province?.name || "").toLowerCase()
      return (
        cleanName.includes(q) ||
        legalName.includes(q) ||
        ruc.includes(q) ||
        province.includes(q)
      )
    })
  }

  if (sort === "name") {
    return [...list].sort((a, b) =>
      formatCoopName(a.razon_social).localeCompare(formatCoopName(b.razon_social), "es")
    )
  }
  return [...list].sort((a, b) => (b.total_assets_usd || 0) - (a.total_assets_usd || 0))
}

export function filterPeerCandidates(
  entities: EntitySummary[],
  query: string,
  limit: number = 50
): EntitySummary[] {
  const q = query.trim().toLowerCase()
  return entities
    .filter((e) => {
      if (!q) return true
      const cleanName = formatCoopName(e.razon_social).toLowerCase()
      return (
        cleanName.includes(q) ||
        e.razon_social.toLowerCase().includes(q) ||
        e.ruc.includes(q) ||
        (e.province?.name || "").toLowerCase().includes(q)
      )
    })
    .slice(0, limit)
}

export function resolveEffectiveChartIndicator(
  indicators: BenchmarkingIndicatorRow[] | undefined,
  requestedIndicatorId: string
): string {
  if (!indicators || indicators.length === 0) return requestedIndicatorId
  const exists = indicators.some((i) => i.indicator_id === requestedIndicatorId)
  return exists ? requestedIndicatorId : indicators[0].indicator_id
}

export function filterDimensionIndicators(
  indicators: BenchmarkingIndicatorRow[] | undefined,
  filterText: string
): BenchmarkingIndicatorRow[] {
  if (!indicators) return []
  const q = filterText.trim().toLowerCase()
  if (!q) return indicators
  return indicators.filter(
    (ind) =>
      ind.indicator_name.toLowerCase().includes(q) ||
      ind.indicator_id.toLowerCase().includes(q) ||
      String(ind.seps_ficha_number || "").includes(q)
  )
}

export function buildChartSeriesData(
  benchmarkData: BenchmarkingCompareResponse | undefined,
  indicatorId: string,
  timeRangeMonths: number
): Record<string, string | number | null>[] {
  if (!benchmarkData || !benchmarkData.time_series) return []
  let pts = benchmarkData.time_series[indicatorId] || []

  if (timeRangeMonths > 0 && pts.length > timeRangeMonths) {
    pts = pts.slice(-timeRangeMonths)
  }

  return pts.map((pt) => {
    const pointObj: Record<string, string | number | null> = {
      period: pt.period,
      segment1_baseline: pt.segment1_baseline ?? null,
      country_baseline: pt.country_baseline ?? null
    }
    Object.entries(pt.entity_values).forEach(([ruc, val]) => {
      pointObj[ruc] = val ?? null
    })
    return pointObj
  })
}

export function buildBarComparisonData(
  currentIndicatorMeta: BenchmarkingIndicatorRow | null,
  benchmarkData: BenchmarkingCompareResponse | undefined
): { name: string; value: number; color: string; isBaseline?: boolean }[] {
  if (!currentIndicatorMeta || !benchmarkData?.entities) return []

  const items: { name: string; value: number; color: string; isBaseline?: boolean }[] = []

  if (currentIndicatorMeta.country_baseline !== null) {
    items.push({
      name: "Media Nacional",
      value: Number(currentIndicatorMeta.country_baseline.toFixed(2)),
      color: "#94A3B8",
      isBaseline: true
    })
  }
  if (currentIndicatorMeta.segment1_baseline !== null) {
    items.push({
      name: "Segmento 1",
      value: Number(currentIndicatorMeta.segment1_baseline.toFixed(2)),
      color: "#475569",
      isBaseline: true
    })
  }

  benchmarkData.entities.forEach((ent, idx) => {
    const val = currentIndicatorMeta.entity_values[ent.ruc]
    if (val !== null && val !== undefined) {
      items.push({
        name: formatCoopName(ent.razon_social),
        value: Number(val.toFixed(2)),
        color: ENTITY_PALETTE[idx % ENTITY_PALETTE.length],
        isBaseline: false
      })
    }
  })

  return items
}
