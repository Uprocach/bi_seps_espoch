import type {
  BenchmarkingCompareRequest,
  BenchmarkingCompareResponse,
  ExportRequestPayload,
  BenchmarkingRankingResponse
} from "@/types/camel"

const API_BASE = "/api/v1/pro"

export async function fetchBenchmarkingCompare(
  payload: BenchmarkingCompareRequest
): Promise<BenchmarkingCompareResponse> {
  const res = await fetch(`${API_BASE}/benchmarking/compare`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify(payload)
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(
      errorBody.detail || `Error ${res.status}: Fallo al ejecutar benchmarking multi-entidad.`
    )
  }

  return res.json()
}

export async function downloadExportCsv(payload: ExportRequestPayload): Promise<void> {
  const res = await fetch(`${API_BASE}/export/csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
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
  const res = await fetch(`${API_BASE}/export/excel`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
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
): Promise<BenchmarkingRankingResponse> {
  const query = new URLSearchParams()
  query.append("indicator_id", params.indicator_id)
  if (params.period) query.append("period", params.period)
  if (params.segment && params.segment !== "all") query.append("segment", params.segment)
  if (params.province && params.province !== "all") query.append("province", params.province)
  if (params.rucs && params.rucs.length > 0) {
    params.rucs.forEach((r) => query.append("rucs", r))
  }
  if (params.limit) query.append("limit", String(params.limit))

  const res = await fetch(`${API_BASE}/benchmarking/ranking?${query.toString()}`, {
    method: "GET",
    credentials: "include"
  })

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error(
      errorBody.detail || `Error ${res.status}: Fallo al calcular el ranking nacional de cooperativas.`
    )
  }

  return res.json()
}
