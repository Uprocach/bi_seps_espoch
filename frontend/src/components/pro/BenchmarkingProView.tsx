import React, { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Scale,
  Building2,
  Plus,
  X,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  FileText,
  Loader2,
  Search,
  ShieldAlert,
  Info,
  Layers,
  Trophy,
  Medal,
  Award,
  Check,
  Filter,
  BarChart3,
  MapPin,
  Users,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  SlidersHorizontal,
  RotateCcw
} from "lucide-react"
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine
} from "recharts"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { EntitySummary, FiltersMetadata } from "@/services/apiClient"
import { fetchEntities } from "@/services/apiClient"
import type {
  CamelDimension,
  BenchmarkingCompareRequest,
  TrafficLightStatus,
  CamelEvaluation
} from "@/types/camel"
import {
  fetchBenchmarkingCompare,
  fetchBenchmarkingRanking,
  downloadExportCsv,
  downloadExportExcel
} from "@/services/proClient"
import { useAuthStore } from "@/store/useAuthStore"
import { formatCoopName } from "@/lib/utils"

interface BenchmarkingProViewProps {
  metadata: FiltersMetadata | null
  entities: EntitySummary[]
  initialSelectedRucs?: string[]
}

export type ProTabId = "ranking" | CamelDimension

const PRO_TABS: { id: ProTabId; label: string; icon?: string }[] = [
  { id: "ranking", label: "Ranking de COACs" },
  { id: "capital", label: "Capital y Solvencia" },
  { id: "calidad_de_activos", label: "Calidad de Activos" },
  { id: "manejo_administrativo", label: "Manejo Administrativo" },
  { id: "rentabilidad", label: "Rentabilidad" },
  { id: "liquidez", label: "Liquidez" }
]

// Paleta distinguible para hasta 5 cooperativas en gráficos y matrices (desacoplada del semáforo regulatorio)
const ENTITY_PALETTE = [
  "#0284C7", // Azul Océano / Zafiro (Entidad 1) - Desacoplado del verde óptimo del semáforo regulatorio
  "#7C3AED", // Violeta Imperial (Entidad 2)
  "#D97706", // Ámbar Cálido (Entidad 3)
  "#2563EB", // Azul Real (Entidad 4)
  "#E11D48"  // Carmesí (Entidad 5)
]

export const BenchmarkingProView: React.FC<BenchmarkingProViewProps> = ({
  metadata,
  entities,
  initialSelectedRucs = [
    "0190155722001", // Jardín Azuayo
    "0190115798001"  // JEP
  ]
}) => {
  const { user } = useAuthStore()

  // Selección de Entidades para Benchmarking (1 a 5 máximo)
  const [selectedRucs, setSelectedRucs] = useState<string[]>(initialSelectedRucs)
  const [searchFilter, setSearchFilter] = useState("")
  const [pickerSegmentFilter, setPickerSegmentFilter] = useState<string>("all")
  const [isEntityPickerOpen, setIsEntityPickerOpen] = useState(false)
  const [pickerSort, setPickerSort] = useState<"assets" | "name">("assets")

  // Pestaña Activa: Ranking o Dimensión CAMEL
  const [activeTab, setActiveTab] = useState<ProTabId>("capital")
  const [activeChartIndicator, setActiveChartIndicator] = useState<string>("solvencia_patrimonial")

  // --------------------------------------------------------------------------
  // Estados de Filtros para el Dashboard de la Dimensión CAMEL
  // --------------------------------------------------------------------------
  const [focalRuc, setFocalRuc] = useState<string | "all">("all")
  const [timeRangeMonths, setTimeRangeMonths] = useState<number>(24)
  const [dimensionFilterText, setDimensionFilterText] = useState<string>("")

  // --------------------------------------------------------------------------
  // Estados de Filtros Dinámicos Bidireccionales para el Ranking
  // --------------------------------------------------------------------------
  const [rankingSegment, setRankingSegment] = useState<string>("all")
  const [rankingProvince, setRankingProvince] = useState<string>("all")
  const [rankingSelectedRucs, setRankingSelectedRucs] = useState<string[]>([])
  const [isPeerPickerOpen, setIsPeerPickerOpen] = useState(false)
  const [peerSearchQuery, setPeerSearchQuery] = useState("")

  // Periodos de análisis
  const latestPeriod = metadata?.periods.latest || "2025-12"
  const startPeriod =
    metadata?.periods.available?.[
      Math.max(0, (metadata?.periods.available.length || 24) - 24)
    ] || "2024-01"

  const [fromPeriod] = useState<string>(startPeriod)
  const [toPeriod] = useState<string>(latestPeriod)

  // Estados de exportación
  const [isExportingCsv, setIsExportingCsv] = useState(false)
  const [isExportingExcel, setIsExportingExcel] = useState(false)
  const [exportMessage, setExportMessage] = useState<string | null>(null)

  // 1. Cargar el Directorio Completo de Entidades (Todas las 229 cooperativas de Segmentos 1, 2, 3 y Mutualistas)
  const { data: allEntitiesResp } = useQuery({
    queryKey: ["pro_all_entities_catalog"],
    queryFn: () => fetchEntities({ pageSize: 500 }),
    staleTime: 30 * 60 * 1000
  })

  const fullEntityCatalog = useMemo(() => {
    return allEntitiesResp?.data && allEntitiesResp.data.length > 0
      ? allEntitiesResp.data
      : entities
  }, [allEntitiesResp, entities])

  // Conteos exactos por segmento del catálogo nacional
  const segmentCounts = useMemo(() => {
    const counts = {
      all: fullEntityCatalog.length,
      SEGMENTO_1: 0,
      SEGMENTO_2: 0,
      SEGMENTO_3: 0,
      SEGMENTO_1_MUTUALISTA: 0
    }
    fullEntityCatalog.forEach((e) => {
      if (e.segment === "SEGMENTO_1") counts.SEGMENTO_1++
      else if (e.segment === "SEGMENTO_2") counts.SEGMENTO_2++
      else if (e.segment === "SEGMENTO_3") counts.SEGMENTO_3++
      else if (e.segment === "SEGMENTO_1_MUTUALISTA") counts.SEGMENTO_1_MUTUALISTA++
    })
    return counts
  }, [fullEntityCatalog])

  // --------------------------------------------------------------------------
  // Interdependencia Dinámica Bidireccional: Provincia <-> Segmento en Ranking
  // --------------------------------------------------------------------------
  // Conteo de cooperativas por segmento condicionado a la provincia seleccionada
  const dynamicSegmentCounts = useMemo(() => {
    const pool =
      rankingProvince === "all"
        ? fullEntityCatalog
        : fullEntityCatalog.filter(
            (e) =>
              (e.province?.name || "").toLowerCase() === rankingProvince.toLowerCase() ||
              e.province?.code === rankingProvince
          )

    const counts = {
      all: pool.length,
      SEGMENTO_1: 0,
      SEGMENTO_2: 0,
      SEGMENTO_3: 0,
      SEGMENTO_1_MUTUALISTA: 0
    }
    pool.forEach((e) => {
      if (e.segment === "SEGMENTO_1") counts.SEGMENTO_1++
      else if (e.segment === "SEGMENTO_2") counts.SEGMENTO_2++
      else if (e.segment === "SEGMENTO_3") counts.SEGMENTO_3++
      else if (e.segment === "SEGMENTO_1_MUTUALISTA") counts.SEGMENTO_1_MUTUALISTA++
    })
    return counts
  }, [fullEntityCatalog, rankingProvince])

  // Lista de provincias disponibles y sus conteos condicionados al segmento seleccionado
  const dynamicProvinceOptions = useMemo(() => {
    const pool =
      rankingSegment === "all"
        ? fullEntityCatalog
        : fullEntityCatalog.filter((e) => e.segment === rankingSegment)

    const provMap: Record<string, number> = {}
    pool.forEach((e) => {
      const pName = e.province?.name || "Sin Provincia"
      provMap[pName] = (provMap[pName] || 0) + 1
    })

    return Object.entries(provMap)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name, "es"))
  }, [fullEntityCatalog, rankingSegment])

  // Manejar cambio de provincia con adaptación de segmento si quedara en 0
  const handleProvinceChange = (newProv: string) => {
    setRankingProvince(newProv)
    if (newProv !== "all" && rankingSegment !== "all") {
      const remainingInSeg = fullEntityCatalog.filter(
        (e) =>
          ((e.province?.name || "").toLowerCase() === newProv.toLowerCase() ||
            e.province?.code === newProv) &&
          e.segment === rankingSegment
      ).length
      if (remainingInSeg === 0) {
        setRankingSegment("all")
      }
    }
  }

  // Manejar cambio de segmento con adaptación de provincia si quedara en 0
  const handleSegmentChange = (newSeg: string) => {
    setRankingSegment(newSeg)
    if (newSeg !== "all" && rankingProvince !== "all") {
      const remainingInProv = fullEntityCatalog.filter(
        (e) =>
          e.segment === newSeg &&
          ((e.province?.name || "").toLowerCase() === rankingProvince.toLowerCase() ||
            e.province?.code === rankingProvince)
      ).length
      if (remainingInProv === 0) {
        setRankingProvince("all")
      }
    }
  }

  // 2. Consulta analítica de Benchmarking Multi-Entidad (DuckDB)
  const comparePayload: BenchmarkingCompareRequest = useMemo(
    () => ({
      entity_ids: selectedRucs,
      start_date: fromPeriod,
      end_date: toPeriod,
      camel_dimension: activeTab === "ranking" ? undefined : activeTab
    }),
    [selectedRucs, fromPeriod, toPeriod, activeTab]
  )

  const {
    data: benchmarkData,
    isLoading: isLoadingBenchmark,
    isFetching: isFetchingBenchmark,
    error: benchmarkError
  } = useQuery({
    queryKey: ["benchmarking_compare", comparePayload],
    queryFn: () => fetchBenchmarkingCompare(comparePayload),
    enabled: selectedRucs.length > 0,
    staleTime: 5 * 60 * 1000
  })

  // 3. Consulta analítica de Ranking de COACs por Ficha (DuckDB con soporte para Provincia y hasta 10 RUCs)
  const {
    data: rankingData,
    isLoading: isLoadingRanking,
    isFetching: isFetchingRanking,
    error: rankingError
  } = useQuery({
    queryKey: [
      "benchmarking_ranking",
      activeChartIndicator,
      toPeriod,
      rankingSegment,
      rankingProvince,
      rankingSelectedRucs
    ],
    queryFn: () =>
      fetchBenchmarkingRanking({
        indicator_id: activeChartIndicator,
        period: toPeriod,
        segment: rankingSegment,
        province: rankingProvince,
        rucs: rankingSelectedRucs.length > 0 ? rankingSelectedRucs : undefined,
        limit: 250
      }),
    enabled: activeTab === "ranking",
    staleTime: 3 * 60 * 1000
  })

  // Manejo de Selección de Entidades para Benchmarking (hasta 5)
  const handleAddEntity = (ruc: string) => {
    if (selectedRucs.includes(ruc)) return
    if (selectedRucs.length >= 5) {
      setExportMessage("El comparador permite contrastar un máximo de 5 cooperativas simultáneamente.")
      setTimeout(() => setExportMessage(null), 3500)
      return
    }
    setSelectedRucs((prev) => [...prev, ruc])
    setIsEntityPickerOpen(false)
    setSearchFilter("")
  }

  const handleRemoveEntity = (ruc: string) => {
    if (selectedRucs.length <= 1) {
      setExportMessage("Debe mantener al menos una entidad en el análisis comparativo.")
      setTimeout(() => setExportMessage(null), 3000)
      return
    }
    setSelectedRucs((prev) => prev.filter((r) => r !== ruc))
  }

  // Manejo de Selección de Entidades para Grupo de Ranking Relativo (hasta 10)
  const handleToggleRankingPeer = (ruc: string) => {
    setRankingSelectedRucs((prev) => {
      if (prev.includes(ruc)) {
        return prev.filter((r) => r !== ruc)
      } else {
        if (prev.length >= 10) {
          setExportMessage("El grupo de ranking relativo permite un máximo de 10 cooperativas.")
          setTimeout(() => setExportMessage(null), 3500)
          return prev
        }
        return [...prev, ruc]
      }
    })
  }

  // Descargas masivas
  const handleExportCsv = async () => {
    try {
      setIsExportingCsv(true)
      await downloadExportCsv(comparePayload)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al descargar CSV"
      setExportMessage(msg)
    } finally {
      setIsExportingCsv(false)
    }
  }

  const handleExportExcel = async () => {
    try {
      setIsExportingExcel(true)
      await downloadExportExcel(comparePayload)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al generar Excel"
      setExportMessage(msg)
    } finally {
      setIsExportingExcel(false)
    }
  }

  // Cooperativas candidatas para el buscador modal principal (catálogo completo de todos los segmentos)
  const filteredCandidates = useMemo(() => {
    const q = searchFilter.trim().toLowerCase()
    let list = fullEntityCatalog.filter((e) => {
      if (pickerSegmentFilter !== "all" && e.segment !== pickerSegmentFilter) {
        return false
      }
      if (!q) return true
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

    if (pickerSort === "name") {
      list = [...list].sort((a, b) =>
        formatCoopName(a.razon_social).localeCompare(formatCoopName(b.razon_social), "es")
      )
    } else {
      list = [...list].sort((a, b) => (b.total_assets_usd || 0) - (a.total_assets_usd || 0))
    }

    return list
  }, [fullEntityCatalog, searchFilter, pickerSegmentFilter, pickerSort])

  // Candidatos para el selector de cooperativas del Ranking (hasta 10)
  const peerCandidates = useMemo(() => {
    const q = peerSearchQuery.trim().toLowerCase()
    return fullEntityCatalog
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
      .slice(0, 50)
  }, [fullEntityCatalog, peerSearchQuery])

  // --------------------------------------------------------------------------
  // Datos y Cálculos del Dashboard de la Dimensión CAMEL
  // --------------------------------------------------------------------------
  // Ratios disponibles en la dimensión actual
  const dimensionIndicators = useMemo(() => {
    if (!benchmarkData?.indicators) return []
    let list = benchmarkData.indicators
    if (dimensionFilterText.trim()) {
      const q = dimensionFilterText.toLowerCase()
      list = list.filter(
        (ind) =>
          ind.indicator_name.toLowerCase().includes(q) ||
          ind.indicator_id.toLowerCase().includes(q) ||
          String(ind.seps_ficha_number || "").includes(q)
      )
    }
    return list
  }, [benchmarkData, dimensionFilterText])

  // Asegurar que activeChartIndicator pertenezca a la dimensión o asignar el primero
  useMemo(() => {
    if (activeTab === "ranking") return
    if (benchmarkData?.indicators?.length) {
      const exists = benchmarkData.indicators.some((i) => i.indicator_id === activeChartIndicator)
      if (!exists && benchmarkData.indicators[0]) {
        setActiveChartIndicator(benchmarkData.indicators[0].indicator_id)
      }
    }
  }, [activeTab, benchmarkData, activeChartIndicator])

  // 4 KPIs representativos de alto nivel para la dimensión (Scorecard Ejecutivo Reimaginado)
  const executiveKpis = useMemo(() => {
    if (!benchmarkData?.indicators || benchmarkData.indicators.length === 0) return []
    // Tomamos los primeros 4 indicadores estratégicos de la dimensión
    return benchmarkData.indicators.slice(0, 4)
  }, [benchmarkData])

  // Indicador actualmente seleccionado en detalle
  const currentIndicatorMeta = useMemo(() => {
    if (!benchmarkData?.indicators) return null
    return benchmarkData.indicators.find((i) => i.indicator_id === activeChartIndicator) || benchmarkData.indicators[0] || null
  }, [benchmarkData, activeChartIndicator])

  // Datos para el gráfico de series del indicador seleccionado (con filtro temporal)
  const chartSeriesData = useMemo(() => {
    if (!benchmarkData || !benchmarkData.time_series) return []
    let pts = benchmarkData.time_series[activeChartIndicator] || []

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
  }, [benchmarkData, activeChartIndicator, timeRangeMonths])

  // Datos para el gráfico de barras transversal en el corte más reciente
  const barComparisonData = useMemo(() => {
    if (!currentIndicatorMeta || !benchmarkData?.entities) return []

    const items: { name: string; value: number; color: string; isBaseline?: boolean }[] = []

    // 1. Líneas Base
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

    // 2. Entidades seleccionadas
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
  }, [currentIndicatorMeta, benchmarkData])

  // Renderizador de Badge Semáforo Normativo
  const renderTrafficLightBadge = (
    evalItem: CamelEvaluation | undefined,
    value: number | null,
    unit: string,
    size: "sm" | "md" = "sm"
  ) => {
    if (!evalItem || value === null) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-500">
          N/D
        </span>
      )
    }

    const st: TrafficLightStatus = evalItem.status
    let badgeClasses = ""
    let Icon = CheckCircle2
    let label = "Cumple"

    if (st === "GREEN") {
      badgeClasses = "bg-emerald-50 text-emerald-800 border-emerald-300"
      Icon = CheckCircle2
      label = "Óptimo"
    } else if (st === "YELLOW") {
      badgeClasses = "bg-amber-50 text-amber-800 border-amber-300"
      Icon = AlertTriangle
      label = "Alerta"
    } else {
      badgeClasses = "bg-rose-50 text-rose-800 border-rose-300"
      Icon = ShieldAlert
      label = "Crítico"
    }

    const formattedValue = unit === "percent" ? `${value.toFixed(2)}%` : value.toFixed(2)

    return (
      <div className="group relative inline-flex items-center">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md font-semibold border shadow-xs transition-all cursor-help ${
            size === "md" ? "px-3 py-1.5 text-xs" : "px-2.5 py-1 text-xs"
          } ${badgeClasses}`}
        >
          <Icon className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{formattedValue}</span>
          {size === "md" && <span className="text-[10px] uppercase font-bold tracking-wider ml-1 opacity-80">({label})</span>}
        </span>

        {/* Tooltip normativo accesible */}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-30 w-64 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-xl pointer-events-none leading-snug">
          <p className="font-bold text-amber-300 mb-0.5">
            {evalItem.normative_reference || "Normativa SEPS / COMF"}
          </p>
          <p className="text-slate-200">{evalItem.message}</p>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* 1. Encabezado Minimalista Institucional */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="mint" className="text-[10px] uppercase font-bold tracking-wider">
              Diagnóstico CAMEL • ESPOCH - DI - 060
            </Badge>
            <span className="text-xs text-slate-500 font-mono">
              {user?.name || "Investigador Acreditado"}
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900 font-serif">
            Benchmarking Multi-Entidad & Dashboard CAMEL
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Supervisión analítica de cooperativas contrastadas contra las líneas base del Segmento 1 y la media nacional (SEPS v3.0).
          </p>
        </div>

        {/* Botones de Exportación Masiva */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportCsv}
            disabled={isExportingCsv || isLoadingBenchmark}
            className="text-xs gap-1.5 h-9 border-slate-200 hover:bg-slate-50 text-slate-700"
            title="Descargar microdatos en CSV con streaming directo"
          >
            {isExportingCsv ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-700" />
            ) : (
              <FileText className="w-3.5 h-3.5 text-emerald-700" />
            )}
            <span>Exportar CSV</span>
          </Button>

          <Button
            size="sm"
            onClick={handleExportExcel}
            disabled={isExportingExcel || isLoadingBenchmark}
            className="text-xs gap-1.5 h-9 bg-emerald-700 hover:bg-emerald-800 text-white shadow-xs"
            title="Descargar libro Excel multi-hoja con plantilla verde esmeralda institucional"
          >
            {isExportingExcel ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
            ) : (
              <FileSpreadsheet className="w-3.5 h-3.5 text-white" />
            )}
            <span>Reporte Excel (3 Hojas)</span>
          </Button>
        </div>
      </div>

      {/* Alertas de Notificación */}
      {exportMessage && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{exportMessage}</span>
          </div>
          <button
            onClick={() => setExportMessage(null)}
            className="text-amber-500 hover:text-amber-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 2. Selector de Entidades en Contraste (Multi-Segmento, hasta 5) */}
      <div className="p-4 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-700" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Cooperativas en Contraste
            </span>
            <Badge variant="mint" className="text-[11px] px-2 py-0.5 font-bold">
              {selectedRucs.length} / 5 seleccionadas
            </Badge>
          </div>

          {/* Botón para Abrir Modal de Búsqueda con Todos los Segmentos */}
          {selectedRucs.length < 5 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setIsEntityPickerOpen(true)
                setSearchFilter("")
                setPickerSegmentFilter("all")
              }}
              className="text-xs gap-1.5 h-8 border-emerald-200 text-emerald-800 hover:bg-emerald-50"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Agregar Cooperativa ({fullEntityCatalog.length} disponibles)</span>
            </Button>
          )}
        </div>

        {/* Modal Dialog Ampliado: Selector Universal de Cooperativas */}
        {isEntityPickerOpen && (
          <div
            className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
            onClick={() => setIsEntityPickerOpen(false)}
          >
            <div
              className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150 overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Cabecera del Modal */}
              <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center">
                    <Building2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Agregar Cooperativa al Comparador
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Catálogo nacional ({fullEntityCatalog.length} entidades de Segmentos 1, 2, 3 y Mutualistas)
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsEntityPickerOpen(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Buscador y Controles de Filtro */}
              <div className="p-4 border-b border-slate-100 space-y-3 bg-white">
                <div className="relative">
                  <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Buscar por nombre comercial, razón social o RUC (ej. Chibuleo, Mushuc Runa, Jardín Azuayo, 29 de Octubre)..."
                    value={searchFilter}
                    onChange={(e) => setSearchFilter(e.target.value)}
                    className="w-full pl-9 pr-8 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:bg-white text-slate-900 font-medium"
                    autoFocus
                  />
                  {searchFilter && (
                    <button
                      onClick={() => setSearchFilter("")}
                      className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-1 overflow-x-auto pb-1 text-[11px]">
                    {[
                      { id: "all", label: `Todos (${segmentCounts.all})` },
                      { id: "SEGMENTO_1", label: `Seg 1 (${segmentCounts.SEGMENTO_1})` },
                      { id: "SEGMENTO_2", label: `Seg 2 (${segmentCounts.SEGMENTO_2})` },
                      { id: "SEGMENTO_3", label: `Seg 3 (${segmentCounts.SEGMENTO_3})` },
                      { id: "SEGMENTO_1_MUTUALISTA", label: `Mut (${segmentCounts.SEGMENTO_1_MUTUALISTA})` }
                    ].map((seg) => (
                      <button
                        key={seg.id}
                        onClick={() => setPickerSegmentFilter(seg.id)}
                        className={`px-2.5 py-1 rounded-md font-semibold transition-all whitespace-nowrap ${
                          pickerSegmentFilter === seg.id
                            ? "bg-emerald-700 text-white shadow-xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {seg.label}
                      </button>
                    ))}
                  </div>

                  <div className="flex items-center gap-1.5 flex-shrink-0 text-[11px]">
                    <span className="text-slate-400">Orden:</span>
                    <button
                      onClick={() => setPickerSort("assets")}
                      className={`px-2 py-0.5 rounded border transition-colors ${
                        pickerSort === "assets"
                          ? "bg-slate-800 text-white border-slate-800 font-bold"
                          : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      Por Activos
                    </button>
                    <button
                      onClick={() => setPickerSort("name")}
                      className={`px-2 py-0.5 rounded border transition-colors ${
                        pickerSort === "name"
                          ? "bg-slate-800 text-white border-slate-800 font-bold"
                          : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                      }`}
                    >
                      A-Z
                    </button>
                  </div>
                </div>
              </div>

              {/* Listado con Scroll Completo de Todas las Cooperativas */}
              <div className="overflow-y-auto flex-1 divide-y divide-slate-100 p-2 text-xs">
                {filteredCandidates.length === 0 ? (
                  <div className="p-8 text-center text-slate-400">
                    <p className="font-semibold text-slate-600">No se encontraron cooperativas</p>
                    <p className="text-[11px] mt-1">
                      Prueba con otro término de búsqueda o selecciona otro segmento.
                    </p>
                  </div>
                ) : (
                  filteredCandidates.map((cand) => {
                    const isAlready = selectedRucs.includes(cand.ruc)
                    const cleanName = formatCoopName(cand.razon_social)
                    const segLabel =
                      cand.segment === "SEGMENTO_1"
                        ? "Segmento 1"
                        : cand.segment === "SEGMENTO_2"
                        ? "Segmento 2"
                        : cand.segment === "SEGMENTO_3"
                        ? "Segmento 3"
                        : "Mutualista"

                    const assetsStr = cand.total_assets_usd
                      ? `$${(cand.total_assets_usd / 1_000_000).toFixed(1)}M`
                      : "N/D"

                    return (
                      <div
                        key={cand.ruc}
                        className="p-3 hover:bg-emerald-50/50 rounded-xl transition-colors flex items-center justify-between gap-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p
                              className="font-bold text-slate-900 text-xs truncate"
                              title={cand.razon_social}
                            >
                              {cleanName}
                            </p>
                            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                              {segLabel}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-400 truncate mt-0.5 flex items-center gap-2">
                            <span className="font-mono text-slate-500">
                              RUC: {cand.ruc}
                            </span>
                            <span>•</span>
                            <span>{cand.province?.name || "Ecuador"}</span>
                            <span>•</span>
                            <span>
                              Activos:{" "}
                              <strong className="text-slate-600 font-mono">
                                {assetsStr}
                              </strong>
                            </span>
                          </p>
                        </div>

                        {isAlready ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <Check className="w-3.5 h-3.5" /> En Selección
                          </span>
                        ) : (
                          <Button
                            size="sm"
                            onClick={() => handleAddEntity(cand.ruc)}
                            disabled={selectedRucs.length >= 5}
                            className="h-8 text-xs px-3 bg-emerald-700 hover:bg-emerald-800 text-white gap-1 flex-shrink-0"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            <span>Agregar</span>
                          </Button>
                        )}
                      </div>
                    )
                  })
                )}
              </div>

              {/* Pie del Modal */}
              <div className="p-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Mostrando{" "}
                  <strong className="text-slate-700">
                    {filteredCandidates.length}
                  </strong>{" "}
                  de{" "}
                  <strong className="text-slate-700">
                    {fullEntityCatalog.length}
                  </strong>{" "}
                  cooperativas ({selectedRucs.length}/5 seleccionadas)
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEntityPickerOpen(false)}
                  className="text-xs h-7 border-slate-200 hover:bg-slate-100"
                >
                  Cerrar
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Chips de Entidades Seleccionadas con Nombres Limpios */}
        <div className="flex flex-wrap gap-2">
          {benchmarkData?.entities?.map((ent, idx) => {
            const color = ENTITY_PALETTE[idx % ENTITY_PALETTE.length]
            const cleanName = formatCoopName(ent.razon_social)
            return (
              <div
                key={ent.ruc}
                className="inline-flex items-center gap-2 pl-3 pr-2 py-1.5 bg-slate-50 border border-slate-200/80 rounded-lg text-xs"
              >
                <div
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="font-bold text-slate-800" title={ent.razon_social}>
                  {cleanName}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  ({ent.ruc.slice(0, 10)})
                </span>
                <button
                  onClick={() => handleRemoveEntity(ent.ruc)}
                  className="p-1 hover:bg-slate-200 text-slate-400 hover:text-rose-600 rounded transition-colors"
                  title="Remover cooperativa"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )
          })}
        </div>
      </div>

      {/* 3. Barra de Pestañas Principales: Ranking de COACs o Dashboard por Dimensión CAMEL */}
      <div className="border-b border-slate-200/80 flex items-center gap-1 overflow-x-auto pb-1">
        {PRO_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3.5 py-2 text-xs font-semibold rounded-t-lg transition-all border-b-2 whitespace-nowrap flex items-center gap-1.5 ${
              activeTab === tab.id
                ? "border-emerald-700 text-emerald-800 bg-emerald-50/60 font-bold"
                : "border-transparent text-slate-500 hover:text-slate-900"
            }`}
          >
            {tab.id === "ranking" ? (
              <Trophy className="w-3.5 h-3.5 text-amber-500" />
            ) : (
              <BarChart3 className="w-3.5 h-3.5 text-emerald-700" />
            )}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* ========================================================================= */}
      {/* 4. VISTA A: Ranking de COACs (Con Filtros Dinámicos de Provincia y Pares) */}
      {/* ========================================================================= */}
      {activeTab === "ranking" && (
        <div className="space-y-4 animate-in fade-in duration-200">
          {/* Cabecera y Controles Dinámicos del Ranking */}
          <div className="p-4 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-3">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-amber-500" />
                  <h3 className="text-sm font-bold text-slate-900">
                    Ranking Nacional del SFPS •{" "}
                    {rankingData?.indicator.name || "Ratio Seleccionado"}
                  </h3>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Posición macroprudencial según la ficha metodológica oficial{" "}
                  <strong className="text-slate-700">
                    SEPS v3.0 ({rankingData?.indicator.seps_ficha_number ? `Ficha ${rankingData.indicator.seps_ficha_number}` : "CAMEL"})
                  </strong>
                  .
                </p>
              </div>

              {/* Selector de Indicador a Rankear */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-medium">Ficha:</span>
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
                  )) || (
                    <option value="morosidad_cartera_total">
                      Ficha 01: Morosidad de Cartera Total
                    </option>
                  )}
                </select>
              </div>
            </div>

            {/* Barra de Filtros Dinámicos Bidireccionales: Provincia, Segmento y Grupo de Pares */}
            <div className="pt-3 border-t border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap text-xs">
                {/* Filtro Dinámico de Provincia */}
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-700" />
                  <span className="font-semibold text-slate-600">Provincia:</span>
                  <select
                    value={rankingProvince}
                    onChange={(e) => handleProvinceChange(e.target.value)}
                    className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
                  >
                    <option value="all">Todas las Provincias ({dynamicProvinceOptions.reduce((a, b) => a + b.count, 0)})</option>
                    {dynamicProvinceOptions.map((prov) => (
                      <option key={prov.name} value={prov.name}>
                        {prov.name} ({prov.count})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Filtro Dinámico de Segmento (actualizado dinámicamente según la provincia) */}
                <div className="flex items-center gap-1 overflow-x-auto text-[11px] ml-1">
                  {[
                    { id: "all", label: `Todos (${dynamicSegmentCounts.all})` },
                    { id: "SEGMENTO_1", label: `Seg 1 (${dynamicSegmentCounts.SEGMENTO_1})`, disabled: dynamicSegmentCounts.SEGMENTO_1 === 0 },
                    { id: "SEGMENTO_2", label: `Seg 2 (${dynamicSegmentCounts.SEGMENTO_2})`, disabled: dynamicSegmentCounts.SEGMENTO_2 === 0 },
                    { id: "SEGMENTO_3", label: `Seg 3 (${dynamicSegmentCounts.SEGMENTO_3})`, disabled: dynamicSegmentCounts.SEGMENTO_3 === 0 }
                  ].map((seg) => (
                    <button
                      key={seg.id}
                      disabled={seg.disabled}
                      onClick={() => handleSegmentChange(seg.id)}
                      className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                        rankingSegment === seg.id
                          ? "bg-emerald-700 text-white shadow-xs font-bold"
                          : seg.disabled
                          ? "bg-slate-50 text-slate-300 cursor-not-allowed"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {seg.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Selector de Cooperativas Específicas para Ranking Relativo (máximo 10) */}
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsPeerPickerOpen(true)}
                  className={`text-xs gap-1.5 h-8 border ${
                    rankingSelectedRucs.length > 0
                      ? "border-emerald-500 bg-emerald-50 text-emerald-800 font-bold"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <Users className="w-3.5 h-3.5 text-emerald-700" />
                  <span>
                    Grupo de Pares ({rankingSelectedRucs.length}/10)
                  </span>
                </Button>

                {rankingSelectedRucs.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setRankingSelectedRucs([])}
                    className="text-[11px] h-8 px-2 text-rose-600 hover:bg-rose-50 hover:text-rose-700 gap-1"
                    title="Limpiar filtro de cooperativas específicas"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Ver Todos</span>
                  </Button>
                )}
              </div>
            </div>

            {/* Chips de Cooperativas Seleccionadas en el Grupo de Ranking */}
            {rankingSelectedRucs.length > 0 && (
              <div className="p-2.5 bg-emerald-50/60 border border-emerald-200/80 rounded-lg flex items-center justify-between flex-wrap gap-2 text-xs">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-bold text-emerald-900 text-[11px] uppercase tracking-wider">
                    Contraste entre Seleccionadas:
                  </span>
                  {rankingSelectedRucs.map((ruc) => {
                    const ent = fullEntityCatalog.find((e) => e.ruc === ruc)
                    const cleanName = ent ? formatCoopName(ent.razon_social) : ruc
                    return (
                      <span
                        key={ruc}
                        className="inline-flex items-center gap-1 pl-2 pr-1.5 py-0.5 rounded-md bg-white border border-emerald-300 text-emerald-900 text-[11px] font-semibold shadow-2xs"
                      >
                        <span>{cleanName}</span>
                        <button
                          onClick={() => handleToggleRankingPeer(ruc)}
                          className="text-slate-400 hover:text-rose-600 rounded"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    )
                  })}
                </div>
                <span className="text-[11px] text-emerald-700 font-medium">
                  Ranking focalizado exclusivo ({rankingSelectedRucs.length} COACs)
                </span>
              </div>
            )}
          </div>

          {/* Modal para Seleccionar Grupo de Pares en Ranking (Hasta 10) */}
          {isPeerPickerOpen && (
            <div
              className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
              onClick={() => setIsPeerPickerOpen(false)}
            >
              <div
                className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full flex flex-col max-h-[80vh] overflow-hidden animate-in zoom-in-95 duration-150"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-emerald-700" />
                    <div>
                      <h4 className="text-sm font-bold text-slate-900">
                        Seleccionar Grupo de Pares para Ranking
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        Elige de 2 a 10 cooperativas para conocer el ranking exclusivo entre ellas ({rankingSelectedRucs.length}/10 seleccionadas).
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setIsPeerPickerOpen(false)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-3 border-b border-slate-100">
                  <div className="relative">
                    <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Buscar por nombre, RUC o provincia..."
                      value={peerSearchQuery}
                      onChange={(e) => setPeerSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
                      autoFocus
                    />
                  </div>
                </div>

                <div className="overflow-y-auto flex-1 divide-y divide-slate-100 p-2 text-xs">
                  {peerCandidates.map((cand) => {
                    const isChecked = rankingSelectedRucs.includes(cand.ruc)
                    const cleanName = formatCoopName(cand.razon_social)
                    return (
                      <div
                        key={cand.ruc}
                        onClick={() => handleToggleRankingPeer(cand.ruc)}
                        className={`p-2.5 rounded-lg flex items-center justify-between cursor-pointer transition-colors ${
                          isChecked ? "bg-emerald-50/80 font-bold" : "hover:bg-slate-50"
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <p className="text-xs text-slate-900 truncate">{cleanName}</p>
                          <p className="text-[10px] text-slate-400 truncate">
                            {cand.ruc} • {cand.segment} • {cand.province?.name || "Ecuador"}
                          </p>
                        </div>
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {}}
                          className="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500"
                        />
                      </div>
                    )
                  })}
                </div>

                <div className="p-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-xs">
                  <span className="text-slate-500">
                    {rankingSelectedRucs.length} cooperativas seleccionadas para ranking
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setRankingSelectedRucs([])}
                      className="text-xs h-7"
                    >
                      Limpiar
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => setIsPeerPickerOpen(false)}
                      className="text-xs h-7 bg-emerald-700 hover:bg-emerald-800 text-white"
                    >
                      Aplicar ({rankingSelectedRucs.length})
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tarjetas Resumen de Líneas Base y Criterio */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <Card className="border-slate-200/80 bg-white shadow-xs">
              <CardContent className="p-3">
                <p className="text-[10px] text-slate-400 uppercase font-semibold">
                  Criterio de Evaluación
                </p>
                <p className="text-xs font-bold text-slate-800 mt-1">
                  {rankingData?.indicator.polarity === "lower_is_better"
                    ? "Menor Valor = Mejor Puesto"
                    : "Mayor Valor = Mejor Puesto"}
                </p>
                <p className="text-[10px] text-emerald-700 font-medium mt-0.5">
                  {rankingData?.indicator.polarity === "lower_is_better"
                    ? "Menor índice de mora / carga"
                    : "Mayor solvencia y rentabilidad"}
                </p>
              </CardContent>
            </Card>

            <Card className="border-slate-200/80 bg-white shadow-xs">
              <CardContent className="p-3">
                <p className="text-[10px] text-slate-400 uppercase font-semibold">
                  Línea Base Segmento 1
                </p>
                <p className="text-base font-bold font-mono text-slate-900 mt-1">
                  {rankingData?.segment1_baseline !== null && rankingData?.segment1_baseline !== undefined
                    ? `${rankingData.segment1_baseline.toFixed(2)}%`
                    : "N/D"}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Referencia de grandes cooperativas</p>
              </CardContent>
            </Card>

            <Card className="border-slate-200/80 bg-white shadow-xs">
              <CardContent className="p-3">
                <p className="text-[10px] text-slate-400 uppercase font-semibold">
                  Promedio Nacional SFPS
                </p>
                <p className="text-base font-bold font-mono text-slate-900 mt-1">
                  {rankingData?.country_baseline !== null && rankingData?.country_baseline !== undefined
                    ? `${rankingData.country_baseline.toFixed(2)}%`
                    : "N/D"}
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">Media consolidada país</p>
              </CardContent>
            </Card>

            <Card className="border-slate-200/80 bg-white shadow-xs">
              <CardContent className="p-3">
                <p className="text-[10px] text-slate-400 uppercase font-semibold">
                  Entidades Evaluadas
                </p>
                <p className="text-base font-bold font-mono text-emerald-800 mt-1">
                  {rankingData?.total_ranked || 0} Cooperativas
                </p>
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {rankingSelectedRucs.length > 0 ? "Filtro de pares activo" : `Corte: ${rankingData?.period || toPeriod}`}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Tabla de Posiciones Oficial con Puesto Relativo y Puesto Nacional */}
          <div className="bg-white border border-slate-200/80 rounded-xl shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-200/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-emerald-700" />
                <h3 className="text-sm font-bold text-slate-900">
                  Tabla de Posiciones ({rankingData?.ranking?.length || 0} Entidades)
                </h3>
              </div>
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Óptimo
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Alerta
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> Crítico
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 text-slate-700 border-b border-slate-200/80">
                  <tr>
                    <th className="py-3 px-3 font-bold w-20 text-center">Puesto</th>
                    <th className="py-3 px-3 font-bold min-w-[200px]">Cooperativa</th>
                    <th className="py-3 px-3 font-bold min-w-[90px]">Segmento</th>
                    <th className="py-3 px-3 font-bold min-w-[110px]">Provincia</th>
                    <th className="py-3 px-3 font-bold text-right min-w-[100px] text-slate-600">
                      Activos (USD)
                    </th>
                    <th className="py-3 px-3 font-bold text-right min-w-[110px] text-slate-900">
                      Valor Ratio
                    </th>
                    <th className="py-3 px-3 font-bold text-center min-w-[120px]">
                      Semáforo CAMEL
                    </th>
                    <th className="py-3 px-3 font-bold text-right min-w-[110px]">
                      Brecha vs País
                    </th>
                    <th className="py-3 px-3 font-bold text-center w-28">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {isLoadingRanking ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-400">
                        <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-700 mb-2" />
                        Calculando ranking nacional con DuckDB OLAP...
                      </td>
                    </tr>
                  ) : rankingError ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-rose-500 font-medium">
                        Error al cargar el ranking:{" "}
                        {rankingError instanceof Error
                          ? rankingError.message
                          : "Error del servidor"}
                      </td>
                    </tr>
                  ) : rankingData?.ranking?.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-slate-400">
                        No hay entidades que cumplan los filtros seleccionados de segmento y provincia.
                      </td>
                    </tr>
                  ) : (
                    rankingData?.ranking.map((row) => {
                      const isSelected = selectedRucs.includes(row.ruc)
                      const cleanName = formatCoopName(row.razon_social)
                      const segBadge =
                        row.segment === "SEGMENTO_1"
                          ? "Segmento 1"
                          : row.segment === "SEGMENTO_2"
                          ? "Segmento 2"
                          : row.segment === "SEGMENTO_3"
                          ? "Segmento 3"
                          : "Mutualista"

                      // Medallas de podio
                      let rankBadge = (
                        <div className="flex flex-col items-center">
                          <span className="font-mono font-bold text-slate-700">#{row.rank}</span>
                          {row.national_rank && row.national_rank !== row.rank && (
                            <span className="text-[9px] text-slate-400 font-mono">
                              (#{row.national_rank} nac.)
                            </span>
                          )}
                        </div>
                      )

                      if (row.rank === 1) {
                        rankBadge = (
                          <div className="flex flex-col items-center">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold border border-amber-300">
                              <Trophy className="w-3 h-3 text-amber-600" /> #1
                            </span>
                            {row.national_rank && row.national_rank !== 1 && (
                              <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                                (#{row.national_rank} nac.)
                              </span>
                            )}
                          </div>
                        )
                      } else if (row.rank === 2) {
                        rankBadge = (
                          <div className="flex flex-col items-center">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-200 text-slate-800 font-bold border border-slate-300">
                              <Medal className="w-3 h-3 text-slate-600" /> #2
                            </span>
                            {row.national_rank && row.national_rank !== 2 && (
                              <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                                (#{row.national_rank} nac.)
                              </span>
                            )}
                          </div>
                        )
                      } else if (row.rank === 3) {
                        rankBadge = (
                          <div className="flex flex-col items-center">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 font-bold border border-amber-200">
                              <Award className="w-3 h-3 text-amber-700" /> #3
                            </span>
                            {row.national_rank && row.national_rank !== 3 && (
                              <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                                (#{row.national_rank} nac.)
                              </span>
                            )}
                          </div>
                        )
                      }

                      const assetsFormatted = row.total_assets_usd
                        ? `$${(row.total_assets_usd / 1_000_000).toFixed(1)}M`
                        : "N/D"

                      const diffCountry = row.diff_country
                      const isDiffPositive = diffCountry !== null && diffCountry !== undefined && diffCountry > 0

                      return (
                        <tr
                          key={row.ruc}
                          className={`hover:bg-slate-50/80 transition-colors ${
                            isSelected ? "bg-emerald-50/30" : ""
                          }`}
                        >
                          <td className="py-2.5 px-3 text-center">{rankBadge}</td>
                          <td className="py-2.5 px-3">
                            <p className="font-bold text-slate-900" title={row.razon_social}>
                              {cleanName}
                            </p>
                            <p className="text-[10px] text-slate-400 font-mono">
                              RUC: {row.ruc.slice(0, 10)}
                            </p>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                              {segBadge}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-600">
                            {row.province || "Ecuador"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {assetsFormatted}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                            {row.value.toFixed(2)}%
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {renderTrafficLightBadge(row.camel_evaluation, row.value, "percent")}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-xs">
                            {diffCountry !== null && diffCountry !== undefined ? (
                              <span
                                className={
                                  (rankingData?.indicator.polarity === "lower_is_better" && !isDiffPositive) ||
                                  (rankingData?.indicator.polarity === "higher_is_better" && isDiffPositive)
                                    ? "text-emerald-700 font-semibold"
                                    : "text-rose-600 font-semibold"
                                }
                              >
                                {isDiffPositive ? `+${diffCountry.toFixed(2)}%` : `${diffCountry.toFixed(2)}%`}
                              </span>
                            ) : (
                              "N/D"
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            {isSelected ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleRemoveEntity(row.ruc)}
                                className="text-[10px] h-7 px-2 border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 gap-1"
                                title="En contraste. Haz clic para remover"
                              >
                                <Check className="w-3 h-3" />
                                <span>En Contraste</span>
                              </Button>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleAddEntity(row.ruc)}
                                disabled={selectedRucs.length >= 5}
                                className="text-[10px] h-7 px-2 border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 text-slate-700 gap-1"
                                title="Añadir cooperativa al comparador de benchmarking"
                              >
                                <Plus className="w-3 h-3 text-emerald-700" />
                                <span>Comparar</span>
                              </Button>
                            )}
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
      )}

      {/* ========================================================================= */}
      {/* 5. VISTA B: Dashboard Ejecutivo de la Dimensión CAMEL (Filtros, KPIs, Gráficas, Tabla) */}
      {/* ========================================================================= */}
      {activeTab !== "ranking" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Barra de Filtros y Controles del Dashboard */}
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

              {/* Filtros Integrados del Dashboard */}
              <div className="flex items-center gap-2 flex-wrap text-xs">
                {/* Filtro de Cooperativa Focal */}
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

                {/* Filtro de Ventana Temporal */}
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

          {/* 1. KPIs Reimaginados: Scorecard Ejecutivo de Ratios Estratégicos */}
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

                  // Determinar valor focal o promedio
                  let displayVal: number | null = null
                  let displayEval: CamelEvaluation | undefined = undefined

                  if (focalRuc !== "all") {
                    displayVal = ind.entity_values[focalRuc] ?? null
                    displayEval = ind.entity_evaluations[focalRuc]
                  } else {
                    // Valor de la primera entidad seleccionada o promedio
                    const firstRuc = selectedRucs[0]
                    displayVal = firstRuc ? ind.entity_values[firstRuc] ?? null : null
                    displayEval = firstRuc ? ind.entity_evaluations[firstRuc] : undefined
                  }

                  // Brechas vs líneas base
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
                        {/* Cabecera de la tarjeta: Ficha + Polaridad */}
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

                        {/* Nombre del Indicador */}
                        <div>
                          <p
                            className="text-xs font-bold text-slate-900 line-clamp-2 leading-snug min-h-[32px]"
                            title={ind.indicator_name}
                          >
                            {ind.indicator_name}
                          </p>
                        </div>

                        {/* Valor Central y Semáforo Principal */}
                        <div className="flex items-baseline justify-between pt-1">
                          <span className="text-2xl font-bold font-mono tracking-tight text-slate-900">
                            {displayVal !== null ? `${displayVal.toFixed(2)}%` : "N/D"}
                          </span>
                          {renderTrafficLightBadge(displayEval, displayVal, ind.unit, "sm")}
                        </div>

                        {/* Comparativas Directas vs Segmento 1 y vs Media País */}
                        <div className="pt-2 border-t border-slate-100 space-y-1 text-[11px] font-mono text-slate-500">
                          <div className="flex items-center justify-between">
                            <span>Base Seg 1 ({ind.segment1_baseline !== null ? `${ind.segment1_baseline.toFixed(1)}%` : "-"}):</span>
                            {diffSeg1 !== null ? (
                              <span
                                className={
                                  (ind.polarity === "lower_is_better" && diffSeg1 <= 0) ||
                                  (ind.polarity === "higher_is_better" && diffSeg1 >= 0)
                                    ? "text-emerald-700 font-semibold"
                                    : "text-rose-600 font-semibold"
                                }
                              >
                                {diffSeg1 >= 0 ? `+${diffSeg1.toFixed(2)}%` : `${diffSeg1.toFixed(2)}%`}
                              </span>
                            ) : (
                              <span>-</span>
                            )}
                          </div>

                          <div className="flex items-center justify-between">
                            <span>Media País ({ind.country_baseline !== null ? `${ind.country_baseline.toFixed(1)}%` : "-"}):</span>
                            {diffCty !== null ? (
                              <span
                                className={
                                  (ind.polarity === "lower_is_better" && diffCty <= 0) ||
                                  (ind.polarity === "higher_is_better" && diffCty >= 0)
                                    ? "text-emerald-700 font-semibold"
                                    : "text-rose-600 font-semibold"
                                }
                              >
                                {diffCty >= 0 ? `+${diffCty.toFixed(2)}%` : `${diffCty.toFixed(2)}%`}
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

          {/* 2. Sección Gráfica del Dashboard (Temporal + Transversal) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Gráfico 1: Evolución Temporal Multianual */}
            <div className="lg:col-span-2 p-5 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-700" />
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      Evolución Temporal del Ratio
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      Trayectoria histórica de las cooperativas vs líneas base
                    </p>
                  </div>
                </div>

                {/* Selector de Indicador a Graficar */}
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

              {/* Contenedor Recharts Temporal */}
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
                      <YAxis tick={{ fontSize: 11 }} />
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
                          return isNaN(num) ? "N/D" : `${num.toFixed(2)}%`
                        }}
                      />
                      <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />

                      {/* Línea Base: Segmento 1 (Dashed) */}
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

                      {/* Línea Base: Media Nacional (Dotted) */}
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

                      {/* Líneas de las Cooperativas Seleccionadas con Nombres Limpios */}
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

            {/* Gráfico 2: Comparativa Transversal en el Corte Actual */}
            <div className="p-5 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-emerald-700" />
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    Contraste Transversal
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Corte: {toPeriod}
                  </p>
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
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 10 }}
                        width={100}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#064E3B",
                          borderColor: "#047857",
                          borderRadius: "0.5rem",
                          fontSize: "11px",
                          color: "#FFFFFF"
                        }}
                        formatter={(val: unknown) => [`${Number(val).toFixed(2)}%`, "Ratio"]}
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

          {/* 3. Matriz Analítica Exhaustiva de la Dimensión */}
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

              {/* Filtro Rápido de Texto para la Tabla */}
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
                          <div
                            className="font-bold text-slate-900 text-xs"
                            title={ent.razon_social}
                          >
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
                      <td
                        colSpan={6 + selectedRucs.length}
                        className="py-12 text-center text-slate-400"
                      >
                        <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-700 mb-2" />
                        Consultando microdatos DuckDB vectorizados...
                      </td>
                    </tr>
                  ) : benchmarkError ? (
                    <tr>
                      <td
                        colSpan={6 + selectedRucs.length}
                        className="py-8 text-center text-rose-500 font-medium"
                      >
                        Fallo al cargar benchmarking:{" "}
                        {benchmarkError instanceof Error
                          ? benchmarkError.message
                          : "Error del servidor"}
                      </td>
                    </tr>
                  ) : dimensionIndicators.length === 0 ? (
                    <tr>
                      <td
                        colSpan={6 + selectedRucs.length}
                        className="py-8 text-center text-slate-400"
                      >
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
                            {row.segment1_baseline !== null
                              ? `${row.segment1_baseline.toFixed(2)}%`
                              : "N/D"}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                            {row.country_baseline !== null
                              ? `${row.country_baseline.toFixed(2)}%`
                              : "N/D"}
                          </td>

                          {/* Columnas para cada cooperativa con Semáforo Normativo */}
                          {benchmarkData?.entities?.map((ent) => {
                            const val = row.entity_values[ent.ruc]
                            const evalItem = row.entity_evaluations[ent.ruc]
                            return (
                              <td key={ent.ruc} className="py-2.5 px-3 text-center">
                                {renderTrafficLightBadge(evalItem, val, row.unit)}
                              </td>
                            )
                          })}

                          {/* Botón para activar el ratio en los gráficos */}
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
      )}
    </div>
  )
}
export default BenchmarkingProView
