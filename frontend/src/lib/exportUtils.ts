import type { IndicatorSeriesResponse, EntitySummary } from "@/services/apiClient"

export function exportToCsv(data: Record<string, any>[], filename: string) {
  if (!data || data.length === 0) return

  const headers = Object.keys(data[0])
  const rows = [headers.join(",")]

  data.forEach((row) => {
    const values = headers.map((header) => {
      const val = row[header]
      if (val === null || val === undefined) return '""'
      const str = String(val).replace(/"/g, '""')
      return `"${str}"`
    })
    rows.push(values.join(","))
  })

  const csvContent = "\uFEFF" + rows.join("\r\n") // BOM UTF-8 para Excel en español
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function exportSeriesToCsv(data: IndicatorSeriesResponse, filename?: string) {
  if (!data || !data.series || data.series.length === 0) return

  const { indicator, series, period_range } = data
  const name = filename || `SEPS_${indicator.id}_${period_range.from}_${period_range.to}.csv`

  // Encabezados
  const headers = ["Periodo", "Serie", "Nivel", "Valor (%)", "Numerador (USD)", "Denominador (USD)", "Entidades"]
  const rows: string[] = [headers.join(",")]

  series.forEach((s) => {
    s.points.forEach((pt) => {
      rows.push([
        `"${pt.period}"`,
        `"${s.label.replace(/"/g, '""')}"`,
        `"${s.level}"`,
        pt.value !== null && pt.value !== undefined ? pt.value.toFixed(indicator.decimals) : "",
        pt.numerator !== null && pt.numerator !== undefined ? pt.numerator.toFixed(2) : "",
        pt.denominator !== null && pt.denominator !== undefined ? pt.denominator.toFixed(2) : "",
        pt.entity_count
      ].join(","))
    })
  })

  const csvContent = "\uFEFF" + rows.join("\r\n") // BOM UTF-8 para Excel en español
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", name)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function exportEntitiesToCsv(entities: EntitySummary[], filename = "SEPS_Directorio_Cooperativas.csv") {
  if (!entities || entities.length === 0) return

  const headers = ["RUC", "Razón Social", "Tipo", "Segmento", "Provincia", "Activos Totales (USD)", "Primer Periodo", "Último Periodo", "Activa"]
  const rows: string[] = [headers.join(",")]

  entities.forEach((e) => {
    rows.push([
      `"${e.ruc}"`,
      `"${e.razon_social.replace(/"/g, '""')}"`,
      `"${e.entity_type}"`,
      `"${e.segment}"`,
      `"${e.province?.name || ''}"`,
      e.total_assets_usd !== null && e.total_assets_usd !== undefined ? e.total_assets_usd.toFixed(2) : "",
      `"${e.first_period}"`,
      `"${e.last_period}"`,
      e.is_active ? "SI" : "NO"
    ].join(","))
  })

  const csvContent = "\uFEFF" + rows.join("\r\n")
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.setAttribute("href", url)
  link.setAttribute("download", filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
