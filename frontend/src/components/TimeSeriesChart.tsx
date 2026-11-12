import React from "react"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts"
import { Download, Printer } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatCurrency, formatPercent } from "@/lib/utils"
import { exportSeriesToCsv } from "@/lib/exportUtils"
import type { IndicatorSeriesResponse, Series, SeriesPoint } from "@/services/apiClient"

// Paleta financiera refinada con tonos pastel
const PASTEL_PALETTE = [
  { stroke: "#059669", fill: "#34d399", name: "Esmeralda Menta" },  // Serie 1
  { stroke: "#d97706", fill: "#fbbf24", name: "Ámbar Dorado" },    // Serie 2
  { stroke: "#0284c7", fill: "#38bdf8", name: "Cielo Suave" },       // Serie 3
  { stroke: "#7c3aed", fill: "#a78bfa", name: "Lavanda Pizarra" },   // Serie 4
  { stroke: "#e11d48", fill: "#fb7185", name: "Coral Suave" },       // Serie 5
  { stroke: "#4f46e5", fill: "#818cf8", name: "Índigo Suave" }       // Serie 6
]

interface TimeSeriesChartProps {
  seriesData?: IndicatorSeriesResponse | null
  isLoading?: boolean
  error?: string | null
  canExport?: boolean
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  seriesData,
  isLoading = false,
  error = null,
  canExport = false
}) => {
  if (isLoading) {
    return (
      <Card className="h-96 flex items-center justify-center border-slate-200">
        <div className="flex flex-col items-center gap-2 text-slate-400">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
          <span className="text-xs font-medium">Cargando serie histórica...</span>
        </div>
      </Card>
    )
  }

  if (error || !seriesData || !seriesData.series || seriesData.series.length === 0) {
    return (
      <Card className="h-96 flex items-center justify-center border-slate-200">
        <div className="text-center text-slate-500 max-w-sm px-4">
          <p className="text-sm font-semibold text-slate-700 mb-1">Sin información para graficar</p>
          <p className="text-xs text-slate-400">
            {error || "Selecciona una cooperativa o ajusta los filtros de segmento para visualizar las tendencias."}
          </p>
        </div>
      </Card>
    )
  }

  const { indicator, series, period_range } = seriesData

  // 1. Pivotar los puntos de todas las series para que Recharts los consuma por periodo
  const periodMap = new Map<string, any>()
  series.forEach((s: Series) => {
    const seriesKey = s.key
    s.points.forEach((pt: SeriesPoint) => {
      if (!periodMap.has(pt.period)) {
        periodMap.set(pt.period, { period: pt.period })
      }
      const entry = periodMap.get(pt.period)
      entry[seriesKey] = pt.value
      entry[`${seriesKey}_num`] = pt.numerator
      entry[`${seriesKey}_den`] = pt.denominator
      entry[`${seriesKey}_count`] = pt.entity_count
    })
  })

  const chartData = Array.from(periodMap.values()).sort((a, b) =>
    a.period.localeCompare(b.period)
  )

  // Custom Tooltip Financiero
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null

    return (
      <div className="rounded-xl border border-slate-200 bg-white/95 p-3.5 shadow-lg backdrop-blur-sm text-xs font-sans min-w-[240px]">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
          <span className="font-bold text-slate-800">{label}</span>
          <Badge variant="mint" className="text-[10px]">
            {indicator.short_name}
          </Badge>
        </div>

        <div className="space-y-2">
          {payload.map((item: any) => {
            const seriesObj = series.find((s) => s.key === item.dataKey)
            const num = item.payload[`${item.dataKey}_num`]
            const den = item.payload[`${item.dataKey}_den`]
            const count = item.payload[`${item.dataKey}_count`]

            return (
              <div key={item.dataKey} className="space-y-0.5">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-1.5 truncate max-w-[150px]">
                    <span
                      className="h-2 w-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="font-medium text-slate-700 truncate">
                      {seriesObj?.label || item.dataKey}
                    </span>
                  </div>
                  <span className="font-mono font-bold text-slate-900">
                    {indicator.unit === "usd"
                      ? formatCurrency(item.value)
                      : indicator.unit === "ratio"
                      ? Number(item.value).toFixed(indicator.decimals ?? 2)
                      : formatPercent(item.value, indicator.decimals)}
                  </span>
                </div>
                {num !== undefined && den !== undefined && (
                  <div className="text-[10px] text-slate-400 pl-3.5 flex justify-between font-mono">
                    <span>Num: {formatCurrency(num)}</span>
                    <span>Den: {formatCurrency(den)}</span>
                  </div>
                )}
                {count > 1 && (
                  <div className="text-[10px] text-slate-400 pl-3.5">
                    Entidades activas: <span className="font-semibold text-slate-600">{count}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <Card className="border-slate-200/80 shadow-sm overflow-hidden print:border-none print:shadow-none">
      <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-2 space-y-2 sm:space-y-0">
        <div>
          <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
            <span>Evolución Mensual: {indicator.name}</span>
            <span className="text-xs font-normal text-slate-500 font-mono">
              ({period_range.from} a {period_range.to})
            </span>
          </CardTitle>
          <CardDescription className="text-xs text-slate-500 mt-0.5">
            Metodología Oficial SEPS {indicator.seps_ficha_number ? `(Ficha Nº ${indicator.seps_ficha_number})` : ""} - Agregado por Ratio de Sumas
          </CardDescription>
        </div>

        <div className="flex flex-wrap items-center gap-2 print:hidden">
          <Badge variant="slate" className="text-[11px] font-mono">
            {series.length} {series.length === 1 ? "serie" : "series"}
          </Badge>
          <Badge variant={indicator.polarity === "lower_is_better" ? "gold" : "mint"} className="text-[11px]">
            Unidad: {indicator.unit}
          </Badge>
          {canExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportSeriesToCsv(seriesData)}
              className="h-8 text-xs gap-1.5 text-slate-700 hover:text-emerald-800"
            >
              <Download className="h-3.5 w-3.5 text-emerald-700" /> Exportar CSV
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.print()}
            className="h-8 text-xs gap-1.5 text-slate-600 hover:text-slate-900"
          >
            <Printer className="h-3.5 w-3.5 text-slate-500" /> Imprimir Ficha
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-4 px-2 sm:px-6">
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
              <defs>
                {series.map((s, idx) => {
                  const palette = PASTEL_PALETTE[idx % PASTEL_PALETTE.length]
                  return (
                    <linearGradient
                      key={`grad-${s.key}`}
                      id={`gradient-${s.key}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="5%" stopColor={palette.fill} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={palette.fill} stopOpacity={0.02} />
                    </linearGradient>
                  )
                })}
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis
                dataKey="period"
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={{ stroke: "#e2e8f0" }}
                dy={6}
              />
              <YAxis
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) =>
                  indicator.unit === "usd"
                    ? formatCurrency(v)
                    : indicator.unit === "ratio"
                    ? Number(v).toFixed(2)
                    : `${v}%`
                }
                domain={["dataMin - 0.5", "dataMax + 0.5"]}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ paddingTop: 12, fontSize: 12 }}
                formatter={(val) => {
                  const s = series.find((item) => item.key === val)
                  return <span className="text-slate-700 font-medium text-xs">{s?.label || val}</span>
                }}
              />
              {series.map((s, idx) => {
                const palette = PASTEL_PALETTE[idx % PASTEL_PALETTE.length]
                return (
                  <Area
                    key={s.key}
                    type="monotone"
                    dataKey={s.key}
                    name={s.key}
                    stroke={palette.stroke}
                    strokeWidth={2.2}
                    fillOpacity={1}
                    fill={`url(#gradient-${s.key})`}
                    activeDot={{ r: 5, strokeWidth: 1.5, stroke: "#ffffff" }}
                  />
                )
              })}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
