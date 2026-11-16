import { useState, useMemo, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  fetchEntities,
  downloadExportCsv,
  downloadExportExcel,
  type EntitySummary,
  type FiltersMetadata
} from "@/services/httpClient"
import type { BenchmarkingCompareRequest } from "@/types/camel"
import { useDashboardStore } from "@/store/useDashboardStore"
import {
  useMetadataFiltersQuery,
  useEntitiesQuery,
  useBenchmarkingCompareQuery,
  useBenchmarkingRankingQuery
} from "@/hooks/useIndicatorsQueries"
import {
  type ProTabId,
  computeSegmentCounts,
  computeProvinceOptions,
  resolveProvinceSegmentFilter,
  resolveSegmentProvinceFilter,
  filterAndSortEntities,
  filterPeerCandidates,
  resolveEffectiveChartIndicator,
  filterDimensionIndicators,
  buildChartSeriesData,
  buildBarComparisonData
} from "@/lib/benchmarkingModel"

export interface UseBenchmarkingWorkbenchOptions {
  metadata?: FiltersMetadata | null
  entities?: EntitySummary[]
  initialSelectedRucs?: string[]
}

export function useBenchmarkingWorkbench(options: UseBenchmarkingWorkbenchOptions) {
  const { data: metaQuery } = useMetadataFiltersQuery()
  const { data: entitiesQuery } = useEntitiesQuery({ pageSize: 100 })
  const store = useDashboardStore()

  const metadata = options.metadata !== undefined ? options.metadata : metaQuery || null
  const entities = options.entities !== undefined ? options.entities : entitiesQuery?.data || []

  useEffect(() => {
    if (options.initialSelectedRucs && options.initialSelectedRucs.length > 0) {
      store.setSelectedRucs(options.initialSelectedRucs)
    }
    // Solo sincronizar si se provee explícitamente initialSelectedRucs al montar
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectedRucs = store.selectedRucs

  const [searchFilter, setSearchFilter] = useState("")
  const [pickerSegmentFilter, setPickerSegmentFilter] = useState<string>("all")
  const [isEntityPickerOpen, setIsEntityPickerOpen] = useState(false)
  const [pickerSort, setPickerSort] = useState<"assets" | "name">("assets")

  const [activeTab, setActiveTab] = useState<ProTabId>("capital")
  const [requestedChartIndicator, setActiveChartIndicator] = useState<string>("solvencia_patrimonial")

  const [focalRuc, setFocalRuc] = useState<string | "all">("all")
  const [timeRangeMonths, setTimeRangeMonths] = useState<number>(24)
  const [dimensionFilterText, setDimensionFilterText] = useState<string>("")

  const [rankingSegment, setRankingSegment] = useState<string>("all")
  const [rankingProvince, setRankingProvince] = useState<string>("all")
  const [rankingSelectedRucs, setRankingSelectedRucs] = useState<string[]>([])
  const [isPeerPickerOpen, setIsPeerPickerOpen] = useState(false)
  const [peerSearchQuery, setPeerSearchQuery] = useState("")

  const latestPeriod = metadata?.periods.latest || "2025-12"
  const startPeriod =
    metadata?.periods.available?.[
      Math.max(0, (metadata?.periods.available.length || 24) - 24)
    ] || "2024-01"

  const [fromPeriod] = useState<string>(startPeriod)
  const [toPeriod] = useState<string>(latestPeriod)

  const [isExportingCsv, setIsExportingCsv] = useState(false)
  const [isExportingExcel, setIsExportingExcel] = useState(false)
  const [exportMessage, setExportMessage] = useState<string | null>(null)

  const { data: allEntitiesResp } = useQuery({
    queryKey: ["pro_all_entities_catalog"],
    queryFn: () => fetchEntities({ pageSize: 500 }),
    staleTime: 30 * 60 * 1000
  })

  const fullEntityCatalog: EntitySummary[] = useMemo(() => {
    return (
      (allEntitiesResp?.data && allEntitiesResp.data.length > 0
        ? allEntitiesResp.data
        : entities) || []
    )
  }, [allEntitiesResp, entities])

  const segmentCounts = useMemo(
    () => computeSegmentCounts(fullEntityCatalog, "all"),
    [fullEntityCatalog]
  )

  const dynamicSegmentCounts = useMemo(
    () => computeSegmentCounts(fullEntityCatalog, rankingProvince),
    [fullEntityCatalog, rankingProvince]
  )

  const dynamicProvinceOptions = useMemo(
    () => computeProvinceOptions(fullEntityCatalog, rankingSegment),
    [fullEntityCatalog, rankingSegment]
  )

  const handleProvinceChange = (newProv: string) => {
    const next = resolveProvinceSegmentFilter(fullEntityCatalog, newProv, rankingSegment)
    setRankingProvince(next.province)
    setRankingSegment(next.segment)
  }

  const handleSegmentChange = (newSeg: string) => {
    const next = resolveSegmentProvinceFilter(fullEntityCatalog, newSeg, rankingProvince)
    setRankingSegment(next.segment)
    setRankingProvince(next.province)
  }

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
  } = useBenchmarkingCompareQuery(comparePayload, selectedRucs.length > 0)

  const activeChartIndicator = useMemo(() => {
    if (activeTab === "ranking") return requestedChartIndicator
    return resolveEffectiveChartIndicator(benchmarkData?.indicators, requestedChartIndicator)
  }, [activeTab, benchmarkData?.indicators, requestedChartIndicator])

  const {
    data: rankingData,
    isLoading: isLoadingRanking,
    isFetching: isFetchingRanking,
    error: rankingError
  } = useBenchmarkingRankingQuery(
    {
      indicator_id: activeChartIndicator,
      period: toPeriod,
      segment: rankingSegment,
      province: rankingProvince,
      rucs: rankingSelectedRucs.length > 0 ? rankingSelectedRucs : undefined,
      limit: 250
    },
    activeTab === "ranking"
  )

  const showTempMessage = (msg: string, ms = 3500) => {
    setExportMessage(msg)
    setTimeout(() => setExportMessage(null), ms)
  }

  const handleAddEntity = (ruc: string) => {
    if (selectedRucs.includes(ruc)) return
    if (selectedRucs.length >= 5) {
      showTempMessage("El comparador permite contrastar un máximo de 5 cooperativas simultáneamente.")
      return
    }
    store.setSelectedRucs([...selectedRucs, ruc])
    setIsEntityPickerOpen(false)
    setSearchFilter("")
  }

  const handleRemoveEntity = (ruc: string) => {
    if (selectedRucs.length <= 1) {
      showTempMessage("Debe mantener al menos una entidad en el análisis comparativo.", 3000)
      return
    }
    store.setSelectedRucs(selectedRucs.filter((r) => r !== ruc))
  }

  const handleToggleRankingPeer = (ruc: string) => {
    setRankingSelectedRucs((prev) => {
      if (prev.includes(ruc)) {
        return prev.filter((r) => r !== ruc)
      }
      if (prev.length >= 10) {
        showTempMessage("El grupo de ranking relativo permite un máximo de 10 cooperativas.")
        return prev
      }
      return [...prev, ruc]
    })
  }

  const handleExportCsv = async () => {
    try {
      setIsExportingCsv(true)
      await downloadExportCsv(comparePayload)
    } catch (err: unknown) {
      setExportMessage(err instanceof Error ? err.message : "Error al descargar CSV")
    } finally {
      setIsExportingCsv(false)
    }
  }

  const handleExportExcel = async () => {
    try {
      setIsExportingExcel(true)
      await downloadExportExcel(comparePayload)
    } catch (err: unknown) {
      setExportMessage(err instanceof Error ? err.message : "Error al descargar Excel")
    } finally {
      setIsExportingExcel(false)
    }
  }

  const filteredCandidates = useMemo(
    () =>
      filterAndSortEntities(fullEntityCatalog, {
        query: searchFilter,
        segment: pickerSegmentFilter,
        sort: pickerSort
      }),
    [fullEntityCatalog, searchFilter, pickerSegmentFilter, pickerSort]
  )

  const peerCandidates = useMemo(
    () => filterPeerCandidates(fullEntityCatalog, peerSearchQuery, 50),
    [fullEntityCatalog, peerSearchQuery]
  )

  const dimensionIndicators = useMemo(
    () => filterDimensionIndicators(benchmarkData?.indicators, dimensionFilterText),
    [benchmarkData?.indicators, dimensionFilterText]
  )

  const executiveKpis = useMemo(
    () => (benchmarkData?.indicators ? benchmarkData.indicators.slice(0, 4) : []),
    [benchmarkData?.indicators]
  )

  const currentIndicatorMeta = useMemo(() => {
    if (!benchmarkData?.indicators) return null
    return (
      benchmarkData.indicators.find((i) => i.indicator_id === activeChartIndicator) ||
      benchmarkData.indicators[0] ||
      null
    )
  }, [benchmarkData?.indicators, activeChartIndicator])

  const chartSeriesData = useMemo(
    () => buildChartSeriesData(benchmarkData, activeChartIndicator, timeRangeMonths),
    [benchmarkData, activeChartIndicator, timeRangeMonths]
  )

  const barComparisonData = useMemo(
    () => buildBarComparisonData(currentIndicatorMeta, benchmarkData),
    [currentIndicatorMeta, benchmarkData]
  )

  return {
    metadata,
    selectedRucs,
    activeTab,
    setActiveTab,
    activeChartIndicator,
    setActiveChartIndicator,
    focalRuc,
    setFocalRuc,
    timeRangeMonths,
    setTimeRangeMonths,
    dimensionFilterText,
    setDimensionFilterText,
    rankingSegment,
    rankingProvince,
    rankingSelectedRucs,
    setRankingSelectedRucs,
    isPeerPickerOpen,
    setIsPeerPickerOpen,
    peerSearchQuery,
    setPeerSearchQuery,
    isEntityPickerOpen,
    setIsEntityPickerOpen,
    searchFilter,
    setSearchFilter,
    pickerSegmentFilter,
    setPickerSegmentFilter,
    pickerSort,
    setPickerSort,
    fromPeriod,
    toPeriod,
    fullEntityCatalog,
    segmentCounts,
    dynamicSegmentCounts,
    dynamicProvinceOptions,
    filteredCandidates,
    peerCandidates,
    benchmarkData,
    isLoadingBenchmark,
    isFetchingBenchmark,
    benchmarkError,
    rankingData,
    isLoadingRanking,
    isFetchingRanking,
    rankingError,
    dimensionIndicators,
    executiveKpis,
    currentIndicatorMeta,
    chartSeriesData,
    barComparisonData,
    isExportingCsv,
    isExportingExcel,
    exportMessage,
    clearExportMessage: () => setExportMessage(null),
    handleProvinceChange,
    handleSegmentChange,
    handleAddEntity,
    handleRemoveEntity,
    handleToggleRankingPeer,
    handleExportCsv,
    handleExportExcel
  }
}
