import React from "react"
import {
  Building2,
  X,
  ArrowRight,
  ShieldAlert,
  TrendingUp,
  Building,
  Droplets,
  Settings,
  Layers
} from "lucide-react"
import { KPICards } from "@/components/KPICards"
import { FiltersBar } from "@/components/FiltersBar"
import { TimeSeriesChart } from "@/components/TimeSeriesChart"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import type {
  FiltersMetadata,
  EntitySummary,
  IndicatorSeriesResponse,
  AggregationLevel,
  SegmentCode
} from "@/services/apiClient"
import type { UserRole } from "@/components/Sidebar"
import {
  CAMEL_DIMENSIONS,
  EXTENDED_CATALOG,
  type IndicatorCategory
} from "@/data/extendedCatalog"

interface DashboardViewProps {
  metadata: FiltersMetadata | null
  selectedIndicator: string
  onSelectIndicator: (id: string) => void
  kpiValues: Record<string, { value: number | null }>
  level: AggregationLevel
  onLevelChange: (level: AggregationLevel) => void
  selectedSegments: SegmentCode[]
  onToggleSegment: (code: SegmentCode) => void
  selectedProvince: string
  onProvinceChange: (code: string) => void
  fromPeriod: string
  toPeriod: string
  onFromChange: (val: string) => void
  onToChange: (val: string) => void
  selectedRucs: string[]
  onRemoveRuc: (ruc: string) => void
  seriesData: IndicatorSeriesResponse | null
  loadingSeries: boolean
  seriesError: string | null
  entities: EntitySummary[]
  onNavigateToBenchmarking: () => void
  selectedDimension: "all" | IndicatorCategory
  userRole: UserRole
  onUnlockAccredited: () => void
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  metadata,
  selectedIndicator,
  onSelectIndicator,
  kpiValues,
  level,
  onLevelChange,
  selectedSegments,
  onToggleSegment,
  selectedProvince,
  onProvinceChange,
  fromPeriod,
  toPeriod,
  onFromChange,
  onToChange,
  selectedRucs,
  onRemoveRuc,
  seriesData,
  loadingSeries,
  seriesError,
  entities,
  onNavigateToBenchmarking,
  selectedDimension,
  userRole,
  onUnlockAccredited
}) => {
  const isAccredited = userRole === "accredited"
  const currentDimMeta = CAMEL_DIMENSIONS.find((d) => d.id === selectedDimension)

  // Indicadores de la dimensión seleccionada
  const dimAllIndicators = EXTENDED_CATALOG.filter(
    (i) => i.category === selectedDimension
  )
  const dimPublicIndicators = dimAllIndicators.filter((i) => i.access === "public")
  const dimAccreditedIndicators = dimAllIndicators.filter(
    (i) => i.access === "accredited"
  )

  const getDimensionIcon = (id: IndicatorCategory) => {
    switch (id) {
      case "calidad_de_activos":
        return ShieldAlert
      case "rentabilidad":
        return TrendingUp
      case "capital":
        return Building
      case "liquidez":
        return Droplets
      case "manejo_administrativo":
        return Settings
      default:
        return Layers
    }
  }

  const DimIcon = currentDimMeta ? getDimensionIcon(currentDimMeta.id) : Layers

  return (
    <div className="space-y-5 w-full">
      {/* CABECERA MINIMALISTA SI HAY UNA DIMENSIÓN SELECCIONADA */}
      {selectedDimension !== "all" && currentDimMeta && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-2xs">
                <DimIcon className="h-4 w-4" />
              </span>
              <h2 className="text-base sm:text-lg font-bold font-serif tracking-tight text-slate-900">
                Dashboard de {currentDimMeta.name}
              </h2>
              <Badge variant="mint" className="text-[10px] uppercase font-bold">
                {currentDimMeta.badge}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed max-w-4xl">
              {currentDimMeta.description} <span className="text-slate-300 mx-1">•</span> <span className="font-mono text-[11px] text-emerald-700">{currentDimMeta.normativeFocus}</span>
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Badge variant="mint" className="text-xs px-2.5 py-1">
              {dimPublicIndicators.length} Indicadores Disponibles
            </Badge>
            {isAccredited && dimAccreditedIndicators.length > 0 && (
              <Badge variant="gold" className="text-xs px-2.5 py-1">
                +{dimAccreditedIndicators.length} Fichas Adicionales
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* SECCIÓN 1: BARRA DE FILTROS (SUPERIOR, ENTRE TÍTULO Y KPIS) */}
      <section>
        <FiltersBar
          level={level}
          onLevelChange={onLevelChange}
          segments={metadata?.segments || []}
          selectedSegments={selectedSegments}
          onToggleSegment={onToggleSegment}
          provinces={metadata?.provinces || []}
          selectedProvince={selectedProvince}
          onProvinceChange={onProvinceChange}
          periods={metadata?.periods.available || []}
          fromPeriod={fromPeriod}
          toPeriod={toPeriod}
          onFromChange={onFromChange}
          onToChange={onToChange}
        />
      </section>

      {/* BANNER DE COOPERATIVAS SELECCIONADAS (MODO INDIVIDUAL / COMPARADOR) */}
      {level === "entity" && (
        <section className="bg-emerald-50/70 border border-emerald-200/80 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="p-1 rounded-md bg-emerald-100 text-emerald-800">
              <Building2 className="h-4 w-4" />
            </div>
            <span className="font-semibold text-emerald-950">
              Cooperativas en análisis ({selectedRucs.length}):
            </span>
            <div className="flex flex-wrap items-center gap-1.5">
              {selectedRucs.map((r) => {
                const ent = entities.find((e) => e.ruc === r)
                return (
                  <Badge
                    key={r}
                    variant="mint"
                    className="gap-1 py-1 px-2.5 bg-white border border-emerald-300 text-emerald-900 shadow-2xs"
                  >
                    <span className="font-semibold truncate max-w-[200px]">
                      {ent?.razon_social || r}
                    </span>
                    {selectedRucs.length > 1 && (
                      <button
                        type="button"
                        onClick={() => onRemoveRuc(r)}
                        className="hover:text-rose-600 ml-1 p-0.5 rounded"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </Badge>
                )
              })}
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={onNavigateToBenchmarking}
            className="text-xs h-7 text-emerald-800 border-emerald-300 hover:bg-emerald-100/50 gap-1"
          >
            <span>Diagnóstico CAMEL</span>
            <ArrowRight className="h-3 w-3" />
          </Button>
        </section>
      )}

      {/* SECCIÓN 2: KPI CARDS */}
      {selectedDimension === "all" ? (
        // VISIÓN GLOBAL: 5 KPIS FIJOS (1 POR GRUPO CAMEL)
        <section>
          <KPICards
            indicators={metadata?.indicators || []}
            selectedIndicator={selectedIndicator}
            onSelectIndicator={onSelectIndicator}
            kpiValues={kpiValues}
            periodLabel={metadata?.periods.latest}
          />
        </section>
      ) : (
        // MODO DIMENSIÓN ESPECIALIZADA: INDICADORES DEL GRUPO EN UNA SOLA FILA
        <section className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-600" />
                Indicadores de {currentDimMeta?.shortName} (Cierre {metadata?.periods.latest || "2025-12"})
              </span>
              <span className="text-[11px] text-slate-400 font-medium">
                Haz clic en una tarjeta para proyectar su evolución histórica en la gráfica inferior
              </span>
            </div>

            {/* GRID DE 4 COLUMNAS PARA MANTENER TODOS LOS INDICADORES EN UNA SOLA FILA */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
              {dimPublicIndicators.map((ind) => {
                const isSelected = selectedIndicator === ind.id
                const val = kpiValues[ind.id]?.value
                const isLowerBetter = ind.polarity === "lower_is_better"

                return (
                  <Card
                    key={ind.id}
                    onClick={() => {
                      if (ind.is_live) onSelectIndicator(ind.id)
                    }}
                    className={`transition-all duration-200 relative overflow-hidden group bg-white shadow-2xs hover:shadow-md border ${
                      ind.is_live ? "cursor-pointer" : ""
                    } ${
                      isSelected
                        ? "border-emerald-600 bg-gradient-to-b from-emerald-50/50 to-white ring-2 ring-emerald-600/20"
                        : "border-slate-200/90 hover:border-emerald-300"
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-600 via-teal-500 to-amber-500" />
                    )}

                    <CardHeader className="p-4 pb-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100/70 px-1.5 py-0.5 rounded font-mono">
                          Ficha #{ind.seps_ficha_number}
                        </span>
                        {isSelected ? (
                          <Badge variant="mint" className="text-[9px] px-1.5 py-0">
                            En Gráfico
                          </Badge>
                        ) : ind.is_live ? (
                          <Badge variant="mint" className="text-[9px] px-1.5 py-0">
                            Serie en Vivo
                          </Badge>
                        ) : (
                          <Badge variant="slate" className="text-[9px] px-1.5 py-0">
                            Ficha Normativa
                          </Badge>
                        )}
                      </div>
                      <CardTitle className="text-sm font-bold text-slate-900 mt-1 truncate" title={ind.name}>
                        {ind.short_name}
                      </CardTitle>
                      <CardDescription className="text-xs text-slate-500 line-clamp-1">
                        {ind.description}
                      </CardDescription>
                    </CardHeader>

                    <CardContent className="p-4 pt-2">
                      <div className="flex items-baseline justify-between mb-2">
                        <div>
                          {!ind.is_live && (
                            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block font-sans">
                              Umbral Regulatorio:
                            </span>
                          )}
                          <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
                            {val !== null && val !== undefined
                              ? `${val.toFixed(ind.decimals)}%`
                              : isSelected && seriesData?.series?.[0]?.points?.length
                              ? `${seriesData.series[0].points[seriesData.series[0].points.length - 1].value?.toFixed(ind.decimals)}%`
                              : (ind.regulatory_threshold?.split(": ")[1] || ind.regulatory_threshold || "Ref. SEPS")}
                          </div>
                        </div>
                        <Badge
                          variant={isLowerBetter ? "gold" : "mint"}
                          className="text-[10px]"
                        >
                          {ind.is_live ? (isLowerBetter ? "Menor es mejor" : "Mayor es mejor") : "Meta SEPS"}
                        </Badge>
                      </div>

                      <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-100 flex items-center justify-between">
                        <span className="truncate max-w-[130px] text-[10px]">{ind.regulatory_threshold || "Referencial SEPS"}</span>
                        {ind.is_live ? (
                          <span className="text-emerald-700 font-semibold group-hover:underline text-[11px]">
                            Graficar →
                          </span>
                        ) : (
                          <span className="text-slate-400 font-medium text-[10px]">
                            Ficha Técnica V3.0
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>

          {/* Fichas Avanzadas: Visibles para el usuario acreditado */}
          {isAccredited && dimAccreditedIndicators.length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-amber-500" />
                  Fichas Especializadas ({dimAccreditedIndicators.length})
                </span>
                <Badge variant="gold" className="text-[10px]">
                  Acreditado
                </Badge>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {dimAccreditedIndicators.map((ind) => (
                  <Card
                    key={ind.id}
                    className="border border-amber-200/90 bg-amber-50/20 transition-all hover:shadow-xs"
                  >
                    <CardHeader className="p-3.5 pb-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-amber-900 bg-amber-100 px-1.5 py-0.5 rounded font-mono">
                          Ficha #{ind.seps_ficha_number}
                        </span>
                        <Badge variant="gold" className="text-[10px]">
                          Acreditado
                        </Badge>
                      </div>
                      <CardTitle className="text-xs font-bold text-slate-900 mt-1 truncate">
                        {ind.name}
                      </CardTitle>
                    </CardHeader>

                    <CardContent className="p-3.5 pt-1 space-y-2">
                      <p className="text-[11px] text-slate-600 line-clamp-2">
                        {ind.description}
                      </p>

                      <div className="rounded bg-slate-900 text-slate-100 p-2 text-[10px] font-mono">
                        <span className="text-emerald-400 font-semibold block truncate">
                          {ind.formula_display}
                        </span>
                        <span className="text-slate-400 block truncate text-[9px] mt-0.5">
                          {ind.components_description}
                        </span>
                      </div>

                      <div className="text-[10px] text-slate-500 pt-1">
                        <span className="font-semibold text-slate-700">Norma:</span>{" "}
                        {ind.regulatory_threshold || "Referencial"}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* SECCIÓN 3: GRÁFICO DE SERIES DE TIEMPO RECHARTS (UN SOLO INDICADOR ACTIVO A LA VEZ) */}
      <section>
        <TimeSeriesChart
          seriesData={seriesData}
          isLoading={loadingSeries}
          error={seriesError}
          canExport={isAccredited}
        />
      </section>
    </div>
  )
}
