import React, { useState, useEffect } from "react"
import {
  Scale,
  ShieldCheck,
  Lock,
  Sparkles,
  Building2,
  Plus,
  X,
  TrendingUp,
  Download,
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  ArrowRight
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell
} from "@/components/ui/table"
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts"
import type { UserRole } from "@/components/Sidebar"
import type { EntitySummary, FiltersMetadata, IndicatorMeta } from "@/services/apiClient"
import { fetchIndicatorSeries, fetchBenchmarkMatrix } from "@/services/apiClient"
import { exportToCsv } from "@/lib/exportUtils"

interface BenchmarkingViewProps {
  userRole: UserRole
  onUnlockAccredited: () => void
  metadata: FiltersMetadata | null
  entities: EntitySummary[]
  selectedRucs: string[]
  onToggleEntity: (ruc: string) => void
  onRemoveRuc: (ruc: string) => void
}

interface BenchmarkRow {
  indicatorId: string
  indicatorName: string
  category: string
  threshold: string
  unit: string
  polarity: "higher_is_better" | "lower_is_better" | "neutral"
  entityValues: Record<string, number | null>
  segment1Avg: number | null
  countryAvg: number | null
}

export const REGULATORY_CAMEL_THRESHOLDS: Record<
  string,
  { label: string; good: (val: number) => boolean; warn: (val: number) => boolean; alertMessage: string; alertMsg?: string }
> = {
  // Ficha 1: Suficiencia Patrimonial (Patrimonio / Activos Inmovilizados Netos)
  solvencia_patrimonial: {
    label: "Meta SEPS: ≥ 100.0%",
    good: (v) => v >= 100.0,
    warn: (v) => v >= 80.0 && v < 100.0,
    alertMessage: "Patrimonio insuficiente para absorber activos improductivos"
  },
  // Ficha 5: Morosidad de Cartera Total
  morosidad_cartera_total: {
    label: "Prudencial: ≤ 5.0%",
    good: (v) => v <= 5.0 + 1e-5,
    warn: (v) => v > 5.0 && v <= 8.0,
    alertMessage: "Cartera improductiva sobrepasa el estándar prudencial"
  },
  // Ficha 18: Cobertura de Cartera Improductiva
  cobertura_cartera_improductiva: {
    label: "Mínimo SEPS: ≥ 100.0%",
    good: (v) => v >= 100.0 - 1e-5,
    warn: (v) => v >= 85.0 && v < 100.0,
    alertMessage: "Provisiones acumuladas deficitarias frente al saldo en mora"
  },
  // Ficha 52: Liquidez Inmediata
  liquidez_inmediata: {
    label: "Prudencial: ≥ 18.0%",
    good: (v) => v >= 18.0 - 1e-5,
    warn: (v) => v >= 14.0 && v < 18.0,
    alertMessage: "Disponibilidades insuficientes para obligaciones exigibles"
  },
  // Ficha 35: ROA
  roa: {
    label: "Deseable: ≥ 1.0%",
    good: (v) => v >= 1.0 - 1e-5,
    warn: (v) => v >= 0.5 && v < 1.0,
    alertMessage: "Excedente neto sobre activos inferior al umbral de sostenibilidad"
  },
  // Ficha 34: ROE
  roe: {
    label: "Deseable: ≥ 8.0%",
    good: (v) => v >= 8.0 - 1e-5,
    warn: (v) => v >= 4.0 && v < 8.0,
    alertMessage: "Retorno sobre patrimonio bajo la inflación / costo de oportunidad"
  },
  // Ficha 62: Solvencia Legal ACPR (Patrimonio Técnico Constituido / Activos Ponderados por Riesgo)
  seps_62_solvencia: {
    label: "Legal SEPS: ≥ 9.0% / Prudencial: ≥ 14.0%",
    good: (v) => v >= 14.0 - 1e-5,
    warn: (v) => v >= 9.0 && v < 14.0,
    alertMessage: "Solvencia legal bajo el estándar prudencial (mínimo legal obligatorio: 9.0%)"
  },
  intermediacion_financiera: {
    label: "Rango 85% - 105%",
    good: (v) => v >= 85.0 && v <= 105.0,
    warn: (v) => (v >= 75.0 && v < 85.0) || (v > 105.0 && v <= 115.0),
    alertMessage: "Desbalance entre captaciones y colocaciones"
  },
  eficiencia_operativa: {
    label: "Deseable < 5.0%",
    good: (v) => v <= 5.0 + 1e-5,
    warn: (v) => v > 5.0 && v <= 7.0,
    alertMessage: "Gastos operativos elevados frente al activo"
  }
}

export const CAMEL_THRESHOLDS = REGULATORY_CAMEL_THRESHOLDS

export const BenchmarkingView: React.FC<BenchmarkingViewProps> = ({
  userRole,
  onUnlockAccredited,
  metadata,
  entities,
  selectedRucs,
  onToggleEntity,
  onRemoveRuc
}) => {
  const isAccredited = userRole === "accredited"
  const latestPeriod = metadata?.periods.latest || "2025-12"

  const [benchmarkRows, setBenchmarkRows] = useState<BenchmarkRow[]>([])
  const [loadingData, setLoadingData] = useState(false)
  const [chartIndicator, setChartIndicator] = useState<string>("morosidad_cartera_total")
  const [addEntityQuery, setAddEntityQuery] = useState("")

  // Cargar valores comparativos de la última fecha (Mitigación Cascada N+1 con endpoint consolidado y fallback Promise.all)
  useEffect(() => {
    if (!isAccredited || !metadata || selectedRucs.length === 0) return

    async function loadBenchmarkData() {
      setLoadingData(true)
      try {
        // Intentar primero el endpoint consolidado en una sola petición
        try {
          const matrixRes = await fetchBenchmarkMatrix(selectedRucs, latestPeriod)
          if (matrixRes && matrixRes.matrix && matrixRes.matrix.length > 0) {
            const rows: BenchmarkRow[] = matrixRes.matrix.map((item) => {
              const thresholdConfig = CAMEL_THRESHOLDS[item.indicator_id] || {
                label: "Ref. Sector",
                good: () => true,
                warn: () => false,
                alertMsg: "Sin umbral normativo"
              }
              return {
                indicatorId: item.indicator_id,
                indicatorName: item.indicator_name,
                category: item.category,
                threshold: thresholdConfig.label,
                unit: item.unit,
                polarity: (item.polarity as any) || "higher_is_better",
                entityValues: item.entity_values,
                segment1Avg: item.segment1_avg,
                countryAvg: item.country_avg
              }
            })
            setBenchmarkRows(rows)
            return
          }
        } catch {
          // Fallback a Promise.all por lotes si el endpoint consolidado no responde
        }

        // Ejecución concurrente por lotes con Promise.all (~300 ms en lugar de 12 s de cascada serial)
        const benchmarkPromises = (metadata?.indicators || []).map(async (ind) => {
          const thresholdConfig = CAMEL_THRESHOLDS[ind.id] || {
            label: "Ref. Sector",
            good: () => true,
            warn: () => false,
            alertMsg: "Sin umbral normativo"
          }

          const [entSeriesRes, segRes, countryRes] = await Promise.all([
            fetchIndicatorSeries({
              indicator: ind.id,
              level: "entity",
              ruc: selectedRucs,
              from: latestPeriod,
              to: latestPeriod
            }).catch(() => null),
            fetchIndicatorSeries({
              indicator: ind.id,
              level: "segment",
              segment: ["SEGMENTO_1"],
              from: latestPeriod,
              to: latestPeriod
            }).catch(() => null),
            fetchIndicatorSeries({
              indicator: ind.id,
              level: "country",
              from: latestPeriod,
              to: latestPeriod
            }).catch(() => null)
          ])

          const entityValues: Record<string, number | null> = {}
          selectedRucs.forEach((r) => {
            const s = entSeriesRes?.series.find((x) => x.key === r)
            entityValues[r] = s && s.points.length > 0 ? s.points[0].value : null
          })

          const segment1Val =
            segRes?.series[0]?.points[0]?.value !== undefined
              ? segRes.series[0].points[0].value
              : null
          const countryVal =
            countryRes?.series[0]?.points[0]?.value !== undefined
              ? countryRes.series[0].points[0].value
              : null

          return {
            indicatorId: ind.id,
            indicatorName: ind.name,
            category: ind.category,
            threshold: thresholdConfig.label,
            unit: ind.unit,
            polarity: (ind.polarity as any) || "higher_is_better",
            entityValues,
            segment1Avg: segment1Val,
            countryAvg: countryVal
          }
        })

        const rows = await Promise.all(benchmarkPromises)
        setBenchmarkRows(rows)
      } catch (err) {
        console.error("Error al cargar datos de benchmark:", err)
      } finally {
        setLoadingData(false)
      }
    }

    loadBenchmarkData()
  }, [isAccredited, metadata, selectedRucs, latestPeriod])

  // Presets de cooperativas para benchmarking rápido
  const handleSelectPreset = (rucs: string[]) => {
    rucs.forEach((r) => {
      if (!selectedRucs.includes(r)) onToggleEntity(r)
    })
  }

  // Exportar matriz a CSV
  const handleExportMatrix = () => {
    if (benchmarkRows.length === 0) return
    const exportData = benchmarkRows.map((row) => {
      const item: Record<string, any> = {
        Indicador: row.indicatorName,
        Categoría: row.category,
        Umbral_SEPS: row.threshold
      }
      selectedRucs.forEach((r) => {
        const ent = entities.find((e) => e.ruc === r)
        const name = ent ? ent.razon_social : r
        item[name] = row.entityValues[r] !== null ? `${row.entityValues[r]}%` : "N/D"
      })
      item["Promedio_Segmento_1"] = row.segment1Avg !== null ? `${row.segment1Avg}%` : "N/D"
      item["Promedio_Nacional"] = row.countryAvg !== null ? `${row.countryAvg}%` : "N/D"
      return item
    })

    exportToCsv(exportData, `Benchmarking_ESPOCH_DI060_${latestPeriod}.csv`)
  }

  // Prepara datos para el gráfico comparativo de barras
  const currentChartRow = benchmarkRows.find((r) => r.indicatorId === chartIndicator)
  const chartData = [
    ...selectedRucs.map((r) => {
      const ent = entities.find((e) => e.ruc === r)
      return {
        name: ent ? ent.razon_social.replace(/COOPERATIVA DE AHORRO Y CR[EÉ]DITO /gi, "").slice(0, 18) : r,
        value: currentChartRow?.entityValues[r] ?? 0,
        type: "entity"
      }
    }),
    {
      name: "Media Segmento 1",
      value: currentChartRow?.segment1Avg ?? 0,
      type: "benchmark"
    },
    {
      name: "Media Nacional",
      value: currentChartRow?.countryAvg ?? 0,
      type: "benchmark"
    }
  ]

  // SI EL USUARIO ESTÁ EN MODO PÚBLICO: MOSTRAR GATE INSTITUCIONAL
  if (!isAccredited) {
    return (
      <div className="space-y-6">
        <div className="relative overflow-hidden rounded-3xl border border-emerald-200/90 bg-gradient-to-br from-emerald-950 via-slate-900 to-emerald-900 text-white p-8 sm:p-12 shadow-2xl">
          <div className="relative z-10 max-w-3xl space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full bg-amber-400/10 border border-amber-400/30 px-3.5 py-1 text-xs font-semibold text-amber-300">
              <Lock className="h-3.5 w-3.5" />
              <span>Módulo Reservado para Investigadores y Miembros Acreditados ESPOCH - DI - 060</span>
            </div>

            <h2 className="text-2xl sm:text-4xl font-bold font-serif tracking-tight leading-tight text-white">
              Benchmarking Pro & Matriz de Diagnóstico CAMEL
            </h2>

            <p className="text-sm sm:text-base text-emerald-100/90 leading-relaxed font-light">
              Este módulo permite a Directores, Unidades de Riesgo y Auditores comparar en tiempo real
              hasta 5 cooperativas de forma simultánea, contrastándolas contra la media ponderada del
              Segmento 1 y aplicando semáforos regulatorios de supervisión SEPS.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div className="rounded-xl bg-white/5 border border-white/10 p-4 space-y-1.5 backdrop-blur-sm">
                <div className="flex items-center gap-2 font-semibold text-amber-300 text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Comparativa Multi-Entidad</span>
                </div>
                <p className="text-xs text-slate-300">
                  Visualiza brechas de colocación, morosidad y rentabilidad entre entidades pares del sector.
                </p>
              </div>

              <div className="rounded-xl bg-white/5 border border-white/10 p-4 space-y-1.5 backdrop-blur-sm">
                <div className="flex items-center gap-2 font-semibold text-amber-300 text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Semáforo Regulatorio SEPS</span>
                </div>
                <p className="text-xs text-slate-300">
                  Evaluación automática frente a umbrales normativos COMF (solvencia 9%/14%, cobertura 100%).
                </p>
              </div>
            </div>

            <div className="pt-4 flex flex-col sm:flex-row items-center gap-3">
              <Button
                variant="secondary"
                size="lg"
                onClick={onUnlockAccredited}
                className="w-full sm:w-auto font-bold text-sm h-11 px-6 shadow-lg shadow-amber-500/20 gap-2 text-slate-900 bg-amber-400 hover:bg-amber-300"
              >
                <Sparkles className="h-4 w-4 text-emerald-950" />
                <span>Simular Sesión Acreditada (Desbloquear Módulo)</span>
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // SI EL USUARIO ESTÁ EN MODO ACREDITADO: MOSTRAR BENCHMARKING PRO COMPLETO
  return (
    <div className="space-y-6">
      {/* 1. Selector de Entidades en Comparación */}
      <Card className="border-amber-200/70 bg-gradient-to-br from-amber-50/40 via-white to-white shadow-sm">
        <CardHeader className="pb-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-amber-600" />
                <CardTitle className="text-base font-bold text-slate-900">
                  Cooperativas en Comparación (Cierre {latestPeriod})
                </CardTitle>
                <Badge variant="gold" className="text-[10px]">
                  Modo Acreditado Activo
                </Badge>
              </div>
              <CardDescription className="text-xs text-slate-500 mt-1">
                Selecciona hasta 5 cooperativas para auditar sus indicadores CAMEL y compararlas con las medias del sector.
              </CardDescription>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleExportMatrix}
              className="text-xs h-8 gap-1.5 border-amber-300 text-amber-900 hover:bg-amber-100/60"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-700" />
              <span>Exportar Matriz a CSV</span>
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-1">
          {/* Fila de Chips de Entidades Seleccionadas */}
          <div className="flex flex-wrap items-center gap-2">
            {selectedRucs.map((r) => {
              const ent = entities.find((e) => e.ruc === r)
              return (
                <div
                  key={r}
                  className="flex items-center gap-1.5 bg-white border border-amber-300 text-amber-950 rounded-lg px-2.5 py-1 text-xs font-semibold shadow-2xs"
                >
                  <Building2 className="h-3.5 w-3.5 text-amber-600" />
                  <span className="truncate max-w-[220px]">
                    {ent?.razon_social || r}
                  </span>
                  {selectedRucs.length > 1 && (
                    <button
                      type="button"
                      onClick={() => onRemoveRuc(r)}
                      className="text-slate-400 hover:text-rose-600 ml-1 p-0.5 rounded"
                      title="Quitar de la comparativa"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              )
            })}
          </div>

          {/* Selector de Presets Rápidos */}
          <div className="flex flex-wrap items-center gap-2 text-xs pt-1">
            <span className="text-slate-400 font-medium">Presets recomendados:</span>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(["0190155722001", "0190097510001", "0190011409001"])
              }
              className="px-2.5 py-1 rounded-md bg-slate-100 hover:bg-emerald-50 hover:text-emerald-900 border border-slate-200 text-slate-700 text-[11px] font-medium transition-colors"
            >
              🏛️ Top 3 del Austro (Jardín Azuayo, JEP, CREA)
            </button>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(["1790409277001", "1790064431001", "1790074232001"])
              }
              className="px-2.5 py-1 rounded-md bg-slate-100 hover:bg-emerald-50 hover:text-emerald-900 border border-slate-200 text-slate-700 text-[11px] font-medium transition-colors"
            >
              🏢 Top Pichincha (Cooprogreso, 29 de Octubre, Alianza)
            </button>
          </div>
        </CardContent>
      </Card>

      {/* 2. Gráfico Comparativo de Barras */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-sm font-bold text-slate-800">
                Gráfico Comparativo de Desempeño
              </CardTitle>
              <CardDescription className="text-xs text-slate-500">
                Comparación directa de las entidades seleccionadas frente a las medias del sector
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-medium">Indicador:</span>
              <select
                aria-label="Indicador para gráfico comparativo"
                value={chartIndicator}
                onChange={(e) => setChartIndicator(e.target.value)}
                className="h-8 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {metadata?.indicators.map((ind) => (
                  <option key={ind.id} value={ind.id}>
                    {ind.short_name || ind.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 15, right: 20, left: 0, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 11 }}
                  unit="%"
                  domain={[0, "auto"]}
                />
                <Tooltip
                  formatter={(value: any) => [`${Number(value).toFixed(2)}%`, "Valor"]}
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    borderRadius: "0.75rem",
                    border: "1px solid #e2e8f0",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                  }}
                />
                <Bar
                  dataKey="value"
                  fill="#059669"
                  radius={[6, 6, 0, 0]}
                  name="Indicador (%)"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* 3. Matriz de Diagnóstico CAMEL y Semáforo Regulatorio */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-sm font-bold text-slate-800">
                Matriz de Diagnóstico CAMEL y Semáforo Regulatorio SEPS
              </CardTitle>
              <CardDescription className="text-xs text-slate-500">
                Semaforización automática: Verde (cumple prudencial), Amarillo (alerta preventiva), Rojo (incumplimiento).
              </CardDescription>
            </div>
            {loadingData && (
              <span className="text-xs text-emerald-700 animate-pulse font-medium">
                Sincronizando datos...
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/80">
                  <TableHead className="font-bold text-slate-700 min-w-[200px]">
                    Indicador CAMEL
                  </TableHead>
                  <TableHead className="font-bold text-slate-700 min-w-[120px]">
                    Umbral SEPS
                  </TableHead>
                  {selectedRucs.map((r) => {
                    const ent = entities.find((e) => e.ruc === r)
                    return (
                      <TableHead key={r} className="font-bold text-slate-900 text-center min-w-[140px]">
                        <span className="block truncate max-w-[140px] mx-auto font-serif" title={ent?.razon_social}>
                          {ent ? ent.razon_social.replace(/COOPERATIVA DE AHORRO Y CR[EÉ]DITO /gi, "") : r}
                        </span>
                      </TableHead>
                    )
                  })}
                  <TableHead className="font-bold text-slate-700 text-center bg-slate-100/50 min-w-[120px]">
                    Media Segmento 1
                  </TableHead>
                  <TableHead className="font-bold text-slate-700 text-center bg-slate-100/80 min-w-[120px]">
                    Media País
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {benchmarkRows.map((row) => {
                  const thresholdConfig = CAMEL_THRESHOLDS[row.indicatorId]
                  return (
                    <TableRow key={row.indicatorId} className="hover:bg-slate-50/50 transition-colors">
                      <TableCell className="font-medium text-xs text-slate-900">
                        <div>
                          <span>{row.indicatorName}</span>
                          <span className="block text-[10px] text-slate-400 capitalize">
                            {row.category.replace(/_/g, " ")}
                          </span>
                        </div>
                      </TableCell>

                      <TableCell className="text-xs font-mono text-slate-600">
                        <Badge variant="slate" className="text-[10px] font-normal">
                          {row.threshold}
                        </Badge>
                      </TableCell>

                      {/* Valores por entidad con semáforo */}
                      {selectedRucs.map((r) => {
                        const val = row.entityValues[r]
                        if (val === null || val === undefined) {
                          return (
                            <TableCell key={r} className="text-center text-xs text-slate-400 font-mono">
                              N/D
                            </TableCell>
                          )
                        }

                        const isGood = thresholdConfig ? thresholdConfig.good(val) : true
                        const isWarn = thresholdConfig ? thresholdConfig.warn(val) : false
                        const msg = thresholdConfig?.alertMessage || thresholdConfig?.alertMsg || "Alerta regulatoria"
                        const alertTitle = !isGood
                          ? msg
                          : isWarn
                          ? `Alerta preventiva: ${msg}`
                          : "Cumple con el umbral prudencial SEPS"

                        let statusBadge = (
                          <Badge
                            variant="mint"
                            className="text-[11px] font-mono px-2 py-0.5 cursor-help"
                            title={alertTitle}
                          >
                            {val.toFixed(2)}%
                          </Badge>
                        )
                        if (isWarn) {
                          statusBadge = (
                            <Badge
                              variant="gold"
                              className="text-[11px] font-mono px-2 py-0.5 bg-amber-100 text-amber-900 border-amber-300 cursor-help"
                              title={alertTitle}
                            >
                              ⚠️ {val.toFixed(2)}%
                            </Badge>
                          )
                        } else if (!isGood) {
                          statusBadge = (
                            <Badge
                              variant="negative"
                              className="text-[11px] font-mono px-2 py-0.5 bg-rose-100 text-rose-800 border-rose-300 cursor-help"
                              title={alertTitle}
                            >
                              🚨 {val.toFixed(2)}%
                            </Badge>
                          )
                        }

                        return (
                          <TableCell key={r} className="text-center font-medium">
                            {statusBadge}
                          </TableCell>
                        )
                      })}

                      {/* Promedios de referencia */}
                      <TableCell className="text-center text-xs font-mono font-semibold text-slate-700 bg-slate-50/50">
                        {row.segment1Avg !== null ? `${row.segment1Avg.toFixed(2)}%` : "N/D"}
                      </TableCell>
                      <TableCell className="text-center text-xs font-mono font-semibold text-slate-700 bg-slate-50/80">
                        {row.countryAvg !== null ? `${row.countryAvg.toFixed(2)}%` : "N/D"}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
