import React from "react"
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Layers,
  Loader2,
  Scale,
  Search,
  SlidersHorizontal,
  TrendingUp
} from "lucide-react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { CamelEvaluation } from "@/types/camel"
import type { useBenchmarkingWorkbench } from "@/hooks/useBenchmarkingWorkbench"
import { ENTITY_PALETTE } from "@/lib/benchmarkingModel"
import { TrafficLightBadge } from "@/components/benchmarking/TrafficLightBadge"
import { formatCoopName, formatIndicatorValue } from "@/lib/utils"

interface CamelDimensionPanelProps {
  workbench: ReturnType<typeof useBenchmarkingWorkbench>
}

export const CamelDimensionPanel: React.FC<CamelDimensionPanelProps> = ({ workbench }) => {
  const {
    activeTab,
    selectedRucs,
    activeChartIndicator,
    setActiveChartIndicator,
    focalRuc,
    setFocalRuc,
    timeRangeMonths,
    setTimeRangeMonths,
    dimensionFilterText,
    setDimensionFilterText,
    toPeriod,
    benchmarkData,
    isLoadingBenchmark,
    isFetchingBenchmark,
    benchmarkError,
    dimensionIndicators,
    executiveKpis,
    currentIndicatorMeta,
    chartSeriesData,
    barComparisonData
  } = workbench

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      <div className="p-4 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-emerald-700" />
              <h3 className="text-sm font-bold text-slate-900 capitalize">
                Dashboard: {activeTab.replace(/_/g, " ")}
              </h3>
              <Badge variant="mint" className="text-[10px] font-bold">
                {dimensionIndicators.length} Ratios SEPS v3.0
              </Badge>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Supervisión macroprudencial integrada con semáforo normativo, evolución temporal y matriz comparativa.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap text-xs">
            <div className="flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
              <span className="font-semibold text-slate-600">Enfoque:</span>
              <select
                value={focalRuc}
                onChange={(e) => setFocalRuc(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
              >
                <option value="all">Todas en Contraste ({selectedRucs.length})</option>
                {benchmarkData?.entities?.map((ent) => (
                  <option key={ent.ruc} value={ent.ruc}>
                    {formatCoopName(ent.razon_social)}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg text-[11px] font-medium">
              {[
                { months: 12, label: "12M" },
                { months: 24, label: "24M" },
                { months: 0, label: "Todo" }
              ].map((t) => (
                <button
                  key={t.months}
                  onClick={() => setTimeRangeMonths(t.months)}
                  className={`px-2 py-1 rounded transition-colors ${
                    timeRangeMonths === t.months
                      ? "bg-white text-slate-900 shadow-2xs font-bold"
                      : "text-slate-500 hover:text-slate-900"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-emerald-700" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Ratios Estratégicos de la Dimensión (Scorecard Normativo)
            </h4>
          </div>
          <span className="text-[11px] text-slate-400">
            Haz clic en cualquier tarjeta para sincronizar las gráficas y análisis
          </span>
        </div>

        {isLoadingBenchmark ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((n) => (
              <div key={n} className="h-36 bg-slate-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            {executiveKpis.map((ind) => {
              const isSelected = activeChartIndicator === ind.indicator_id

              let displayVal: number | null = null
              let displayEval: CamelEvaluation | undefined = undefined

              if (focalRuc !== "all") {
                displayVal = ind.entity_values[focalRuc] ?? null
                displayEval = ind.entity_evaluations[focalRuc]
              } else {
                const firstRuc = selectedRucs[0]
                displayVal = firstRuc ? ind.entity_values[firstRuc] ?? null : null
                displayEval = firstRuc ? ind.entity_evaluations[firstRuc] : undefined
              }

              const diffSeg1 =
                displayVal !== null && ind.segment1_baseline !== null
                  ? displayVal - ind.segment1_baseline
                  : null
              const diffCty =
                displayVal !== null && ind.country_baseline !== null
                  ? displayVal - ind.country_baseline
                  : null

              return (
                <Card
                  key={ind.indicator_id}
                  onClick={() => setActiveChartIndicator(ind.indicator_id)}
                  className={`cursor-pointer transition-all hover:shadow-md border text-left ${
                    isSelected
                      ? "ring-2 ring-emerald-600 border-emerald-500 bg-emerald-50/40 shadow-xs"
                      : "border-slate-200/80 hover:border-slate-300 bg-white"
                  }`}
                >
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono">
                        Ficha {ind.seps_ficha_number ?? "-"}
                      </span>
                      <span className="text-[10px] font-medium text-slate-500 flex items-center gap-1">
                        {ind.polarity === "lower_is_better" ? (
                          <span className="text-emerald-700 font-semibold flex items-center gap-0.5">
                            <ArrowDownRight className="w-3 h-3" /> Menor es Mejor
                          </span>
                        ) : (
                          <span className="text-emerald-700 font-semibold flex items-center gap-0.5">
                            <ArrowUpRight className="w-3 h-3" /> Mayor es Mejor
                          </span>
                        )}
                      </span>
                    </div>

                    <div>
                      <p
                        className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug min-h-[32px]"
                        title={ind.indicator_name}
                      >
                        {ind.indicator_name}
                      </p>
                    </div>

                    <div className="flex items-baseline justify-between pt-1">
                      <span className="text-2xl font-bold font-mono tracking-tight text-slate-900">
                        {formatIndicatorValue(displayVal, ind.unit)}
                      </span>
                      <TrafficLightBadge evalItem={displayEval} value={displayVal} unit={ind.unit} size="sm" />
                    </div>

                    <div className="pt-2 border-t border-slate-100 space-y-1 text-[11px] font-mono text-slate-500">
                      <div className="flex items-center justify-between">
                        <span>
                          Base Seg 1 (
                          {formatIndicatorValue(ind.segment1_baseline, ind.unit, {
                            decimals: 1,
                            fallback: "-"
                          })}
                          ):
                        </span>
                        {diffSeg1 !== null ? (
                          <span
                            className={
                              (ind.polarity === "lower_is_better" && diffSeg1 <= 0) ||
                              (ind.polarity === "higher_is_better" && diffSeg1 >= 0)
                                ? "text-emerald-700 font-semibold"
                                : "text-rose-600 font-semibold"
                            }
                          >
                            {formatIndicatorValue(diffSeg1, ind.unit, { signed: true })}
                          </span>
                        ) : (
                          <span>-</span>
                        )}
                      </div>

                      <div className="flex items-center justify-between">
                        <span>
                          Media País (
                          {formatIndicatorValue(ind.country_baseline, ind.unit, {
                            decimals: 1,
                            fallback: "-"
                          })}
                          ):
                        </span>
                        {diffCty !== null ? (
                          <span
                            className={
                              (ind.polarity === "lower_is_better" && diffCty <= 0) ||
                              (ind.polarity === "higher_is_better" && diffCty >= 0)
                                ? "text-emerald-700 font-semibold"
                                : "text-rose-600 font-semibold"
                            }
                          >
                            {formatIndicatorValue(diffCty, ind.unit, { signed: true })}
                          </span>
                        ) : (
                          <span>-</span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 p-5 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-700" />
              <div>
                <h4 className="text-sm font-bold text-slate-900">Evolución Temporal del Ratio</h4>
                <p className="text-[11px] text-slate-400">
                  Trayectoria histórica de las cooperativas vs líneas base
                </p>
              </div>
            </div>

            <select
              value={activeChartIndicator}
              onChange={(e) => setActiveChartIndicator(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-600 max-w-xs font-medium"
            >
              {benchmarkData?.indicators?.map((ind) => (
                <option key={ind.indicator_id} value={ind.indicator_id}>
                  {ind.seps_ficha_number ? `Ficha ${ind.seps_ficha_number}: ` : ""}
                  {ind.indicator_name}
                </option>
              ))}
            </select>
          </div>

          <div className="h-72 w-full">
            {isLoadingBenchmark ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-700 mr-2" />
                Cargando series históricas...
              </div>
            ) : chartSeriesData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                Sin datos temporales para el rango seleccionado.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartSeriesData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => formatIndicatorValue(Number(v), currentIndicatorMeta?.unit)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#064E3B",
                      borderColor: "#047857",
                      borderRadius: "0.5rem",
                      fontSize: "11px",
                      color: "#FFFFFF"
                    }}
                    formatter={(val: unknown) => {
                      const num = typeof val === "number" ? val : Number(val)
                      return formatIndicatorValue(num, currentIndicatorMeta?.unit)
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />

                  <Line
                    type="monotone"
                    dataKey="segment1_baseline"
                    name="Línea Base: Segmento 1"
                    stroke="#475569"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="country_baseline"
                    name="Media Nacional (SFPS)"
                    stroke="#94A3B8"
                    strokeWidth={1.5}
                    strokeDasharray="2 2"
                    dot={false}
                    isAnimationActive={false}
                  />
                  {benchmarkData?.entities?.map((ent, idx) => (
                    <Line
                      key={ent.ruc}
                      type="monotone"
                      dataKey={ent.ruc}
                      name={formatCoopName(ent.razon_social)}
                      stroke={ENTITY_PALETTE[idx % ENTITY_PALETTE.length]}
                      strokeWidth={2.5}
                      dot={{ r: 2 }}
                      activeDot={{ r: 4 }}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-700" />
            <div>
              <h4 className="text-sm font-bold text-slate-900">Contraste Transversal</h4>
              <p className="text-[11px] text-slate-400">Corte: {toPeriod}</p>
            </div>
          </div>

          <div className="h-72 w-full">
            {isLoadingBenchmark ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-700 mr-2" />
                Cargando comparativa...
              </div>
            ) : barComparisonData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-xs">
                Sin datos en el corte seleccionado.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={barComparisonData}
                  layout="vertical"
                  margin={{ top: 10, right: 30, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={100} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#064E3B",
                      borderColor: "#047857",
                      borderRadius: "0.5rem",
                      fontSize: "11px",
                      color: "#FFFFFF"
                    }}
                    formatter={(val: unknown) => {
                      const num = typeof val === "number" ? val : Number(val)
                      const formatted = formatIndicatorValue(num, currentIndicatorMeta?.unit)
                      return [
                        formatted,
                        Number.isNaN(num)
                          ? "Valor"
                          : currentIndicatorMeta?.unit === "usd"
                          ? "Monto"
                          : "Ratio"
                      ]
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {barComparisonData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200/80 rounded-xl shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-emerald-700" />
            <h4 className="text-sm font-bold text-slate-900">
              Matriz Normativa CAMEL ({dimensionIndicators.length} Ratios)
            </h4>
            {isFetchingBenchmark && (
              <span className="flex items-center gap-1 text-[11px] text-emerald-700 font-medium">
                <Loader2 className="w-3 h-3 animate-spin" />
                Actualizando...
              </span>
            )}
          </div>

          <div className="relative max-w-xs w-full">
            <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filtrar ratio por nombre o ficha..."
              value={dimensionFilterText}
              onChange={(e) => setDimensionFilterText(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-700 border-b border-slate-200/80">
              <tr>
                <th className="py-3 px-3 font-bold w-12 text-center">Ficha</th>
                <th className="py-3 px-3 font-bold min-w-[220px]">Indicador Financiero</th>
                <th className="py-3 px-3 font-bold min-w-[100px]">Polaridad</th>
                <th className="py-3 px-3 font-bold text-right min-w-[100px] text-slate-600">
                  Segmento 1
                </th>
                <th className="py-3 px-3 font-bold text-right min-w-[100px] text-slate-600">
                  Nacional
                </th>
                {benchmarkData?.entities?.map((ent, idx) => {
                  const cleanName = formatCoopName(ent.razon_social)
                  return (
                    <th
                      key={ent.ruc}
                      className="py-3 px-3 font-bold text-center min-w-[140px]"
                      style={{
                        borderTop: `3px solid ${ENTITY_PALETTE[idx % ENTITY_PALETTE.length]}`
                      }}
                    >
                      <div className="font-bold text-slate-900 text-xs" title={ent.razon_social}>
                        {cleanName}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono font-normal">
                        RUC: {ent.ruc.slice(0, 10)}
                      </div>
                    </th>
                  )
                })}
                <th className="py-3 px-3 font-bold text-center w-24">Graficar</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoadingBenchmark ? (
                <tr>
                  <td colSpan={6 + selectedRucs.length} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-700 mb-2" />
                    Consultando microdatos DuckDB vectorizados...
                  </td>
                </tr>
              ) : benchmarkError ? (
                <tr>
                  <td colSpan={6 + selectedRucs.length} className="py-8 text-center text-rose-500 font-medium">
                    Fallo al cargar benchmarking:{" "}
                    {benchmarkError instanceof Error ? benchmarkError.message : "Error del servidor"}
                  </td>
                </tr>
              ) : dimensionIndicators.length === 0 ? (
                <tr>
                  <td colSpan={6 + selectedRucs.length} className="py-8 text-center text-slate-400">
                    No hay indicadores que coincidan con la búsqueda.
                  </td>
                </tr>
              ) : (
                dimensionIndicators.map((row) => {
                  const isRowActive = activeChartIndicator === row.indicator_id
                  return (
                    <tr
                      key={row.indicator_id}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isRowActive ? "bg-emerald-50/30" : ""
                      }`}
                    >
                      <td className="py-2.5 px-3 text-center font-mono text-slate-500">
                        {row.seps_ficha_number ?? "-"}
                      </td>
                      <td className="py-2.5 px-3 font-medium text-slate-900">
                        <button
                          onClick={() => setActiveChartIndicator(row.indicator_id)}
                          className="text-left hover:text-emerald-700 transition-colors underline-offset-2 hover:underline"
                          title="Ver evolución temporal en las gráficas"
                        >
                          {row.indicator_name}
                        </button>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-[10px] text-slate-500 flex items-center gap-1">
                          {row.polarity === "lower_is_better" ? (
                            <span className="text-emerald-700 font-medium flex items-center gap-0.5">
                              <ArrowDownRight className="w-3 h-3" /> Menor
                            </span>
                          ) : (
                            <span className="text-emerald-700 font-medium flex items-center gap-0.5">
                              <ArrowUpRight className="w-3 h-3" /> Mayor
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                        {formatIndicatorValue(row.segment1_baseline, row.unit)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                        {formatIndicatorValue(row.country_baseline, row.unit)}
                      </td>

                      {benchmarkData?.entities?.map((ent) => {
                        const val = row.entity_values[ent.ruc]
                        const evalItem = row.entity_evaluations[ent.ruc]
                        return (
                          <td key={ent.ruc} className="py-2.5 px-3 text-center">
                            <TrafficLightBadge evalItem={evalItem} value={val} unit={row.unit} />
                          </td>
                        )
                      })}

                      <td className="py-2.5 px-3 text-center">
                        <Button
                          variant={isRowActive ? "default" : "outline"}
                          size="sm"
                          onClick={() => setActiveChartIndicator(row.indicator_id)}
                          className={`h-6 text-[10px] px-2 gap-1 ${
                            isRowActive
                              ? "bg-emerald-700 text-white"
                              : "border-slate-200 text-slate-600 hover:border-emerald-500 hover:text-emerald-700"
                          }`}
                        >
                          <TrendingUp className="w-3 h-3" />
                          <span>{isRowActive ? "Activo" : "Ver"}</span>
                        </Button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
