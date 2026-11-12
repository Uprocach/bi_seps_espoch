import React from "react"
import {
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
} from "@/services/httpClient"
import type { UserRole } from "@/components/Sidebar"
import {
  CAMEL_DIMENSIONS,
  type IndicatorCategory
} from "@/data/extendedCatalog"
import { useDashboardStore } from "@/store/useDashboardStore"
import { useAuthStore } from "@/store/useAuthStore"
import {
  useMetadataFiltersQuery,
  useIndicatorSeriesQuery,
  useEntitiesQuery
} from "@/hooks/useIndicatorsQueries"

interface DashboardViewProps {
  metadata?: FiltersMetadata | null
  selectedIndicator?: string
  onSelectIndicator?: (id: string) => void
  kpiValues?: Record<string, { value: number | null }>
  level?: AggregationLevel
  onLevelChange?: (level: AggregationLevel) => void
  selectedSegments?: SegmentCode[]
  onToggleSegment?: (code: SegmentCode) => void
  selectedProvince?: string
  onProvinceChange?: (code: string) => void
  fromPeriod?: string
  toPeriod?: string
  onFromChange?: (val: string) => void
  onToChange?: (val: string) => void
  selectedRucs?: string[]
  onRemoveRuc?: (ruc: string) => void
  seriesData?: IndicatorSeriesResponse | null
  loadingSeries?: boolean
  seriesError?: string | null
  entities?: EntitySummary[]
  onNavigateToBenchmarking?: () => void
  selectedDimension?: "all" | IndicatorCategory
  userRole?: UserRole
  onUnlockAccredited?: () => void
}

export const DashboardView: React.FC<DashboardViewProps> = (props) => {
  const store = useDashboardStore()
  const { isAuthenticated, openLoginModal } = useAuthStore()

  // Queries reactivas vía TanStack Query
  const { data: metaQuery } = useMetadataFiltersQuery()
  const metadata = props.metadata !== undefined ? props.metadata : (metaQuery || null)

  const selectedIndicator = props.selectedIndicator ?? store.selectedIndicator
  const level = props.level ?? store.level
  const selectedSegments = props.selectedSegments ?? store.selectedSegments
  const selectedProvince = props.selectedProvince ?? store.selectedProvince
  const fromPeriod = props.fromPeriod ?? store.fromPeriod
  const toPeriod = props.toPeriod ?? store.toPeriod
  const selectedRucs = props.selectedRucs ?? store.selectedRucs
  const selectedDimension = props.selectedDimension ?? store.selectedDimension

  const { data: seriesQuery, isLoading: seriesLoading, error: seriesErrorObj } = useIndicatorSeriesQuery({
    indicator: selectedIndicator,
    level: level,
    segment: level === "segment" ? selectedSegments : undefined,
    province: selectedProvince ? [selectedProvince] : undefined,
    ruc: level === "entity" ? selectedRucs : undefined,
    from: fromPeriod,
    to: toPeriod
  })

  const seriesData = props.seriesData !== undefined ? props.seriesData : (seriesQuery || null)
  const loadingSeries = props.loadingSeries !== undefined ? props.loadingSeries : seriesLoading
  const seriesError = props.seriesError !== undefined ? props.seriesError : (seriesErrorObj ? (seriesErrorObj as Error).message : null)

  const { data: entitiesQuery } = useEntitiesQuery({ pageSize: 100 })
  const entities = props.entities !== undefined ? props.entities : (entitiesQuery?.data || [])

  // Callbacks
  const onSelectIndicator = props.onSelectIndicator ?? store.setSelectedIndicator
  const onLevelChange = props.onLevelChange ?? store.setLevel
  const onToggleSegment = props.onToggleSegment ?? ((code: SegmentCode) => {
    const next = selectedSegments.includes(code)
      ? selectedSegments.filter((c) => c !== code)
      : [...selectedSegments, code]
    store.setSelectedSegments(next)
  })
  const onProvinceChange = props.onProvinceChange ?? store.setSelectedProvince
  const onFromChange = props.onFromChange ?? store.setFromPeriod
  const onToChange = props.onToChange ?? store.setToPeriod
  const onRemoveRuc = props.onRemoveRuc ?? store.toggleRuc
  const onNavigateToBenchmarking = props.onNavigateToBenchmarking ?? (() => store.setActiveView("benchmarking"))
  const onUnlockAccredited = props.onUnlockAccredited ?? openLoginModal
  const userRole = props.userRole ?? (isAuthenticated ? "accredited" : "public")

  // Calcular últimos valores de KPIs
  const computedKpiValues = React.useMemo(() => {
    if (props.kpiValues) return props.kpiValues
    const kpiMap: Record<string, { value: number | null }> = {}
    if (metadata?.indicators) {
      metadata.indicators.forEach((ind) => {
        kpiMap[ind.id] = { value: ind.latest_value ?? null }
      })
    }
    if (seriesData?.series?.[0]?.points?.length) {
      const lastPt = seriesData.series[0].points[seriesData.series[0].points.length - 1]
      if (lastPt?.value !== null && lastPt?.value !== undefined) {
        kpiMap[selectedIndicator] = { value: lastPt.value }
      }
    }
    return kpiMap
  }, [props.kpiValues, metadata, seriesData, selectedIndicator])

  const isAccredited = userRole === "accredited"
  const currentDimMeta = CAMEL_DIMENSIONS.find((d) => d.id === selectedDimension)

  const periodsList = React.useMemo(() => {
    if (metadata?.periods?.available && metadata.periods.available.length > 0) {
      return metadata.periods.available
    }
    if (!metadata?.periods) return ["2024-01", "2024-06", "2024-12", "2025-01", "2025-06", "2025-12"]
    const minP = metadata.periods.min || "2024-01"
    const maxP = metadata.periods.max || "2025-12"
    const [minY, minM] = minP.split("-").map(Number)
    const [maxY, maxM] = maxP.split("-").map(Number)
    const result: string[] = []
    for (let y = minY; y <= maxY; y++) {
      const startMonth = y === minY ? minM : 1
      const endMonth = y === maxY ? maxM : 12
      for (let m = startMonth; m <= endMonth; m++) {
        result.push(`${y}-${String(m).padStart(2, "0")}`)
      }
    }
    return result
  }, [metadata?.periods])

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
                Dashboard: {currentDimMeta.name}
              </h2>
              <Badge variant="mint" className="text-[10px] uppercase font-bold">
                {currentDimMeta.badge}
              </Badge>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed max-w-4xl">
              {currentDimMeta.description} <span className="text-slate-300 mx-1">•</span> <span className="font-mono text-[11px] text-emerald-700">{currentDimMeta.normativeFocus}</span>
            </p>
          </div>
        </div>
      )}

      {/* BLOQUE DE TARJETAS KPI CAMEL (5 INDICADORES BÁSICOS ACORDADOS) */}
      <KPICards
        indicators={metadata?.indicators || []}
        kpiValues={computedKpiValues}
        selectedIndicator={selectedIndicator}
        onSelectIndicator={onSelectIndicator}
        periodLabel={toPeriod}
      />

      {/* BARRA SUPERIOR DE FILTROS GLOBALES */}
      <FiltersBar
        level={level}
        onLevelChange={onLevelChange}
        segments={metadata?.segments || []}
        selectedSegments={selectedSegments}
        onToggleSegment={onToggleSegment}
        provinces={metadata?.provinces || []}
        selectedProvince={selectedProvince}
        onProvinceChange={onProvinceChange}
        periods={periodsList}
        fromPeriod={fromPeriod}
        toPeriod={toPeriod}
        onFromChange={onFromChange}
        onToChange={onToChange}
      />

      {/* GRÁFICO PRINCIPAL DE SERIES DE TIEMPO */}
      <TimeSeriesChart
        seriesData={seriesData}
        isLoading={loadingSeries}
        error={seriesError}
        canExport={userRole !== "public"}
      />

      {/* CALLOUT INFORMATIVO SEGÚN PERFIL INSTITUCIONAL */}
      {!isAccredited ? (
        <Card className="border border-slate-200/80 bg-white/80 shadow-xs">
          <CardHeader className="py-4 px-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <CardTitle className="text-sm font-semibold text-slate-800 flex items-center gap-2 font-serif">
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  Visualización de Estadísticas Sectoriales Abiertas
                </CardTitle>
                <CardDescription className="text-xs text-slate-500">
                  Explorando series históricas oficiales a nivel nacional y por segmento SEPS. Para acceder a microdatos por cooperativa supervisada y diagnósticos CAMEL, active su sesión institucional.
                </CardDescription>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={onUnlockAccredited}
                className="shrink-0 text-xs border-emerald-600/40 text-emerald-800 hover:bg-emerald-50/80 font-medium"
              >
                Acceso Institucional
              </Button>
            </div>
          </CardHeader>
        </Card>
      ) : (
        <Card className="border border-emerald-200/80 bg-emerald-50/30 shadow-xs">
          <CardHeader className="py-4 px-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-0.5">
                <CardTitle className="text-sm font-semibold text-emerald-950 flex items-center gap-2 font-serif">
                  <span className="h-2 w-2 rounded-full bg-emerald-600" />
                  Sesión Institucional Activa • Supervisión Acreditada
                </CardTitle>
                <CardDescription className="text-xs text-emerald-800/80">
                  Acceso completo habilitado a microdatos por cooperativa, diagnóstico y benchmarking CAMEL, bitácora de auditoría forense y exportación de reportes ejecutivos.
                </CardDescription>
              </div>
              <Button
                size="sm"
                onClick={onNavigateToBenchmarking}
                className="shrink-0 text-xs bg-emerald-700 hover:bg-emerald-800 text-white font-medium shadow-2xs"
              >
                Diagnóstico CAMEL
              </Button>
            </div>
          </CardHeader>
        </Card>
      )}
    </div>
  )
}
export default DashboardView
