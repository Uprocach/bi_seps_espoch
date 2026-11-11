import type { components } from "@/types/api"

export type FiltersMetadata = components["schemas"]["FiltersMetadata"]
export type Segment = components["schemas"]["Segment"]
export type Province = components["schemas"]["Province"]
export type IndicatorMeta = components["schemas"]["IndicatorMeta"]
export type EntitySummary = components["schemas"]["EntitySummary"]
export type EntityListResponse = components["schemas"]["EntityListResponse"]
export type IndicatorSeriesResponse = components["schemas"]["IndicatorSeriesResponse"]
export type Series = components["schemas"]["Series"]
export type SeriesPoint = components["schemas"]["SeriesPoint"]
export type SegmentCode = components["schemas"]["SegmentCode"]
export type AggregationLevel = components["schemas"]["AggregationLevel"]
export type IndicatorId = components["schemas"]["IndicatorId"]
export type AuditLogItem = components["schemas"]["AuditLogItem"]
export type AuditLogsListResponse = components["schemas"]["AuditLogsListResponse"]

const API_BASE = "/api/v1"

// Gestión de Sesión Segura (HttpOnly Cookies - Cero persistencia en localStorage)
let inMemoryToken: string | null = null

export function setAuthToken(token: string | null) {
  inMemoryToken = token
}

export function getAuthToken(): string | null {
  return inMemoryToken
}

export async function requestProToken(
  username = "investigador.espoch",
  password = "EspochPro2026#"
): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password, role: "investigador" })
  })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || "No se pudo obtener la sesión institucional Pro")
  }
  return "cookie_session_active"
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {}
  if (inMemoryToken) {
    headers["Authorization"] = `Bearer ${inMemoryToken}`
  }
  return headers
}

export async function fetchMetadataFilters(): Promise<FiltersMetadata> {
  const res = await fetch(`${API_BASE}/metadata/filters?_t=${Date.now()}`, {
    credentials: "include",
    cache: "no-store"
  })
  if (!res.ok) {
    throw new Error(`Error ${res.status}: Fallo al cargar metadatos de filtros`)
  }
  return res.json()
}

export interface ListEntitiesParams {
  segment?: SegmentCode[]
  province?: string[]
  q?: string
  active?: boolean
  sort?: string
  page?: number
  pageSize?: number
}

export async function fetchEntities(params: ListEntitiesParams = {}): Promise<EntityListResponse> {
  const query = new URLSearchParams()
  if (params.segment) {
    params.segment.forEach((s) => query.append("segment", s))
  }
  if (params.province) {
    params.province.forEach((p) => query.append("province", p))
  }
  if (params.q) query.append("q", params.q)
  if (params.active !== undefined) query.append("active", String(params.active))
  if (params.sort) query.append("sort", params.sort)
  if (params.page) query.append("page", String(params.page))
  if (params.pageSize) query.append("page_size", String(params.pageSize))

  const res = await fetch(`${API_BASE}/entities?${query.toString()}`, {
    credentials: "include"
  })
  if (!res.ok) {
    throw new Error(`Error ${res.status}: Fallo al listar entidades`)
  }
  return res.json()
}

export interface IndicatorSeriesParams {
  indicator: string
  level: AggregationLevel
  segment?: SegmentCode[]
  province?: string[]
  ruc?: string[]
  from?: string
  to?: string
}

export async function fetchIndicatorSeries(params: IndicatorSeriesParams): Promise<IndicatorSeriesResponse> {
  const query = new URLSearchParams()
  query.append("indicator", params.indicator)
  query.append("level", params.level)
  if (params.segment) {
    params.segment.forEach((s) => query.append("segment", s))
  }
  if (params.province) {
    params.province.forEach((p) => query.append("province", p))
  }
  if (params.ruc) {
    params.ruc.forEach((r) => query.append("ruc", r))
  }
  if (params.from) query.append("from", params.from)
  if (params.to) query.append("to", params.to)

  const res = await fetch(`${API_BASE}/indicators/series?${query.toString()}`, {
    headers: getAuthHeaders(),
    credentials: "include"
  })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Error ${res.status}: Fallo al obtener series`)
  }
  return res.json()
}

export interface BenchmarkMatrixRow {
  indicator_id: string
  indicator_name: string
  category: string
  unit: string
  polarity: string
  methodological_note?: string | null
  entity_values: Record<string, number | null>
  segment1_avg: number | null
  country_avg: number | null
}

export interface BenchmarkMatrixResponse {
  period: string
  rucs: string[]
  matrix: BenchmarkMatrixRow[]
  generated_at: string
}

export async function fetchBenchmarkMatrix(rucs: string[], period?: string): Promise<BenchmarkMatrixResponse> {
  const query = new URLSearchParams()
  rucs.forEach((r) => query.append("ruc", r))
  if (period) query.append("period", period)

  const res = await fetch(`${API_BASE}/indicators/benchmark-matrix?${query.toString()}`, {
    headers: getAuthHeaders(),
    credentials: "include"
  })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Error ${res.status}: Fallo al obtener matriz de benchmark`)
  }
  return res.json()
}

export async function fetchAuditLogs(params: {
  limit?: number
  offset?: number
  user_sub?: string
  action?: string
  start_date?: string
  end_date?: string
} = {}): Promise<AuditLogsListResponse> {
  const query = new URLSearchParams()
  if (params.limit !== undefined) query.set("limit", params.limit.toString())
  if (params.offset !== undefined) query.set("offset", params.offset.toString())
  if (params.user_sub) query.set("user_sub", params.user_sub)
  if (params.action) query.set("action", params.action)
  if (params.start_date) query.set("start_date", params.start_date)
  if (params.end_date) query.set("end_date", params.end_date)

  const res = await fetch(`${API_BASE}/admin/audit-logs?${query.toString()}`, {
    headers: getAuthHeaders(),
    credentials: "include"
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Error ${res.status}: Fallo al consultar bitácora de auditoría`)
  }

  return res.json()
}
