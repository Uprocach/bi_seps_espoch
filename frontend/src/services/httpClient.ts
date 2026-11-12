/**
 * Cliente HTTP Profundo Institucional (ESPOCH-DI-060 / ADR-0001 / ADR-0004)
 * Centraliza las peticiones de red hacia /api/v1/* y /api/v1/supervision/*
 * Soporte estricto para sesiones mediante cookies HttpOnly (credentials: "include") y errores RFC 9457.
 */

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
export type PipelineStatusResponse = components["schemas"]["PipelineStatusResponse"]
export type PipelineSyncStatusResponse = components["schemas"]["PipelineSyncStatusResponse"]
export type BenchmarkingCompareRequest = components["schemas"]["BenchmarkingCompareRequest"]
export type BenchmarkingCompareResponse = components["schemas"]["BenchmarkingCompareResponse"]
export type BenchmarkingIndicatorRow = components["schemas"]["BenchmarkingIndicatorRow"]
export type BenchmarkingSeriesPoint = components["schemas"]["BenchmarkingSeriesPoint"]
export type ExportRequestPayload = components["schemas"]["ExportRequest"]

const API_BASE = "/api/v1"

/**
 * Función base para peticiones HTTP con manejo estandarizado de cookies y errores RFC 9457
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`
  const config: RequestInit = {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers
    }
  }

  const res = await fetch(url, config)

  if (!res.ok) {
    let errorDetail = `Error ${res.status}: Fallo en la comunicación con el servidor.`
    try {
      const errorBody = await res.json()
      if (errorBody.detail) {
        errorDetail = errorBody.detail
      } else if (errorBody.title) {
        errorDetail = errorBody.title
      }
    } catch {
      // Usar mensaje genérico si no es JSON
    }
    throw new Error(errorDetail)
  }

  return res.json()
}

// ----------------------------------------------------------------------
// Métodos de Catálogos y Filtros
// ----------------------------------------------------------------------

export async function fetchMetadataFilters(): Promise<FiltersMetadata> {
  return request<FiltersMetadata>(`/metadata/filters?_t=${Date.now()}`, {
    cache: "no-store"
  })
}

// ----------------------------------------------------------------------
// Directorio de Entidades
// ----------------------------------------------------------------------

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

  return request<EntityListResponse>(`/entities?${query.toString()}`)
}

// ----------------------------------------------------------------------
// Series Temporales de Indicadores
// ----------------------------------------------------------------------

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

  return request<IndicatorSeriesResponse>(`/indicators/series?${query.toString()}`)
}

// ----------------------------------------------------------------------
// Supervisión Institucional & Benchmarking CAMEL
// ----------------------------------------------------------------------

export async function fetchBenchmarkingCompare(
  payload: BenchmarkingCompareRequest
): Promise<BenchmarkingCompareResponse> {
  return request<BenchmarkingCompareResponse>("/supervision/benchmarking/compare", {
    method: "POST",
    body: JSON.stringify(payload)
  })
}

export interface FetchRankingParams {
  indicator_id: string
  period?: string
  segment?: string
  province?: string
  rucs?: string[]
  limit?: number
}

export async function fetchBenchmarkingRanking(
  params: FetchRankingParams
): Promise<any> {
  const query = new URLSearchParams()
  query.append("indicator_id", params.indicator_id)
  if (params.period) query.append("period", params.period)
  if (params.segment && params.segment !== "all") query.append("segment", params.segment)
  if (params.province && params.province !== "all") query.append("province", params.province)
  if (params.rucs && params.rucs.length > 0) {
    params.rucs.forEach((r) => query.append("rucs", r))
  }
  if (params.limit) query.append("limit", String(params.limit))

  return request(`/supervision/benchmarking/ranking?${query.toString()}`)
}

export async function downloadExportCsv(payload: ExportRequestPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/supervision/export/csv`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Error ${res.status}: Fallo al exportar microdatos CSV.`)
  }

  const blob = await res.blob()
  const contentDisposition = res.headers.get("content-disposition")
  let filename = "espoch_sfps_microdatos.csv"
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  const url = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export async function downloadExportExcel(payload: ExportRequestPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/supervision/export/excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(errorBody.detail || `Error ${res.status}: Fallo al generar reporte Excel.`)
  }

  const blob = await res.blob()
  const contentDisposition = res.headers.get("content-disposition")
  let filename = "espoch_sfps_benchmarking_camel.xlsx"
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match && match[1]) {
      filename = match[1]
    }
  }

  const url = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

// ----------------------------------------------------------------------
// Auditoría Forense & Pipeline Admin
// ----------------------------------------------------------------------

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

  return request<AuditLogsListResponse>(`/admin/audit-logs?${query.toString()}`)
}

export async function fetchPipelineStatus(): Promise<PipelineStatusResponse> {
  return request<PipelineStatusResponse>("/admin/pipeline-status")
}

export async function fetchPipelineSyncStatus(): Promise<PipelineSyncStatusResponse> {
  return request<PipelineSyncStatusResponse>("/admin/pipeline-sync-status")
}
