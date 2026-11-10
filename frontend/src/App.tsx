import React, { useState, useEffect } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Sidebar, type ActiveView, type UserRole } from "@/components/Sidebar"
import { TopBar } from "@/components/TopBar"
import { DashboardView } from "@/components/views/DashboardView"
import { BenchmarkingProView } from "@/components/pro/BenchmarkingProView"
import { CatalogView } from "@/components/views/CatalogView"
import { EntitiesView } from "@/components/views/EntitiesView"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { LoginModal } from "@/components/auth/LoginModal"
import { ChangePasswordModal } from "@/components/auth/ChangePasswordModal"
import { AdminUsersView } from "@/components/views/AdminUsersView"
import { useAuthStore } from "@/store/useAuthStore"
import {
  fetchMetadataFilters,
  fetchEntities,
  fetchIndicatorSeries,
  type FiltersMetadata,
  type EntitySummary,
  type IndicatorSeriesResponse,
  type AggregationLevel,
  type SegmentCode
} from "@/services/apiClient"
import { exportToCsv } from "@/lib/exportUtils"
import type { IndicatorCategory } from "@/data/extendedCatalog"

// Instancia singleton de TanStack Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000
    }
  }
})

const AppContent: React.FC = () => {
  // Store de Autenticación Institucional (Zustand)
  const { user, isAuthenticated, checkAuth, openLoginModal, logout } = useAuthStore()

  // Estado de Navegación y Perfil de Acceso
  const [activeView, setActiveView] = useState<ActiveView>("dashboard")
  const [selectedDimension, setSelectedDimension] = useState<"all" | IndicatorCategory>("all")
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  const userRole: UserRole = isAuthenticated ? "accredited" : "public"

  // Estado de Metadatos
  const [metadata, setMetadata] = useState<FiltersMetadata | null>(null)
  const [loadingMeta, setLoadingMeta] = useState(true)

  // Estado de Filtros de Visualización
  const [selectedIndicator, setSelectedIndicator] = useState<string>("morosidad_cartera_total")
  const [level, setLevel] = useState<AggregationLevel>("country")
  const [selectedSegments, setSelectedSegments] = useState<SegmentCode[]>([
    "SEGMENTO_1",
    "SEGMENTO_2"
  ])
  const [selectedProvince, setSelectedProvince] = useState<string>("")
  const [fromPeriod, setFromPeriod] = useState<string>("2024-01")
  const [toPeriod, setToPeriod] = useState<string>("2025-12")
  const [selectedRucs, setSelectedRucs] = useState<string[]>([
    "0190155722001", // Jardín Azuayo
    "0190115798001"  // JEP
  ])

  // Estado de Datos de Series
  const [seriesData, setSeriesData] = useState<IndicatorSeriesResponse | null>(null)
  const [loadingSeries, setLoadingSeries] = useState(false)
  const [seriesError, setSeriesError] = useState<string | null>(null)

  // Estado de Resumen de KPIs
  const [kpiValues, setKpiValues] = useState<Record<string, { value: number | null }>>({})

  // Estado de Tabla de Entidades
  const [entities, setEntities] = useState<EntitySummary[]>([])
  const [loadingEntities, setLoadingEntities] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [entityPage, setEntityPage] = useState(1)
  const [entityTotalPages, setEntityTotalPages] = useState(1)
  const [entityTotalItems, setEntityTotalItems] = useState(0)

  // 1. Validar sesión HttpOnly y Cargar Metadatos al Iniciar
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    async function loadMeta() {
      try {
        setLoadingMeta(true)
        const meta = await fetchMetadataFilters()
        setMetadata(meta)

        if (meta.periods.available.length > 0) {
          const avail = meta.periods.available
          setToPeriod(meta.periods.latest)
          const startIdx = Math.max(0, avail.length - 24)
          setFromPeriod(avail[startIdx])
        }

        const kpiMap: Record<string, { value: number | null }> = {}
        meta.indicators.forEach((ind: any) => {
          if (ind.latest_value !== undefined && ind.latest_value !== null) {
            kpiMap[ind.id] = { value: ind.latest_value }
          }
        })
        setKpiValues(kpiMap)
      } catch (err: unknown) {
        console.error("Error cargando metadatos:", err)
      } finally {
        setLoadingMeta(false)
      }
    }
    loadMeta()
  }, [])

  // 2. Cargar Serie de Tiempo para el indicador seleccionado
  useEffect(() => {
    async function loadSeries() {
      if (!selectedIndicator) return
      try {
        setLoadingSeries(true)
        setSeriesError(null)

        const res = await fetchIndicatorSeries({
          indicator: selectedIndicator,
          level,
          segment: level === "segment" ? selectedSegments : undefined,
          province: selectedProvince ? [selectedProvince] : undefined,
          ruc: level === "entity" ? selectedRucs : undefined,
          from: fromPeriod,
          to: toPeriod
        })
        setSeriesData(res)

        if (res.series?.[0]?.points?.length) {
          const lastPt = res.series[0].points[res.series[0].points.length - 1]
          if (lastPt?.value !== null && lastPt?.value !== undefined) {
            setKpiValues((prev) => ({
              ...prev,
              [selectedIndicator]: { value: lastPt.value }
            }))
          }
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Error al cargar series temporales."
        setSeriesError(msg)
      } finally {
        setLoadingSeries(false)
      }
    }

    loadSeries()
  }, [
    selectedIndicator,
    level,
    selectedSegments,
    selectedProvince,
    selectedRucs,
    fromPeriod,
    toPeriod
  ])

  // 3. Cargar Directorio de Entidades (con debounce)
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        setLoadingEntities(true)
        const res = await fetchEntities({
          q: searchQuery || undefined,
          province: selectedProvince ? [selectedProvince] : undefined,
          segment: level === "segment" ? selectedSegments : undefined,
          page: entityPage,
          pageSize: 15
        })
        setEntities(res.data)
        setEntityTotalPages(res.pagination.total_pages)
        setEntityTotalItems(res.pagination.total_items)
      } catch (err: unknown) {
        console.error("Error al cargar entidades:", err)
      } finally {
        setLoadingEntities(false)
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [searchQuery, selectedProvince, selectedSegments, level, entityPage])

  const handleToggleSegment = (code: SegmentCode) => {
    setSelectedSegments((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  const handleToggleEntity = (ruc: string) => {
    setSelectedRucs((prev) => {
      if (prev.includes(ruc)) {
        if (prev.length <= 1) return prev
        return prev.filter((r) => r !== ruc)
      } else {
        return prev.length >= 5 ? [...prev.slice(1), ruc] : [...prev, ruc]
      }
    })
  }

  const handleRemoveRuc = (ruc: string) => {
    if (selectedRucs.length > 1) {
      setSelectedRucs((prev) => prev.filter((r) => r !== ruc))
    }
  }

  const handleToggleRole = () => {
    if (isAuthenticated) {
      logout()
    } else {
      openLoginModal()
    }
  }

  const handleSelectDimension = (dim: "all" | IndicatorCategory) => {
    setSelectedDimension(dim)
    setActiveView("dashboard")

    if (dim !== "all") {
      const matching = metadata?.indicators.filter((i) => i.category === dim) || []
      if (matching.length > 0 && !matching.some((i) => i.id === selectedIndicator)) {
        setSelectedIndicator(matching[0].id)
      }
    }
  }

  const handleSelectAndGraph = (indicatorId: string) => {
    setSelectedIndicator(indicatorId)
    const ind = metadata?.indicators.find((i) => i.id === indicatorId)
    if (ind?.category) {
      setSelectedDimension(ind.category as IndicatorCategory)
    }
    setActiveView("dashboard")
  }

  const handleExportGlobal = () => {
    if (!isAuthenticated) return
    if (seriesData && seriesData.series.length > 0) {
      const rows: Record<string, unknown>[] = []
      seriesData.series.forEach((s) => {
        s.points.forEach((p) => {
          rows.push({
            Serie: s.label,
            Clave: s.key,
            Periodo: p.period,
            Valor: p.value,
            Indicador: seriesData.indicator.id
          })
        })
      })
      exportToCsv(rows, `ESPOCH_DI060_${seriesData.indicator.id}_${fromPeriod}_${toPeriod}.csv`)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/70 flex font-sans text-slate-800 antialiased selection:bg-emerald-200">
      {/* Modal de Acreditación Institucional */}
      <LoginModal />
      <ChangePasswordModal />

      {/* Sidebar de Navegación Lateral */}
      <Sidebar
        activeView={activeView}
        onSelectView={setActiveView}
        selectedDimension={selectedDimension}
        onSelectDimension={handleSelectDimension}
        userRole={userRole}
        onToggleRole={handleToggleRole}
        latestPeriod={metadata?.periods.latest}
        totalEntities={entityTotalItems || 39}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        systemRole={user?.role}
      />

      {/* Contenedor Principal */}
      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ease-in-out w-full ${
          isSidebarCollapsed ? "lg:pl-20" : "lg:pl-72"
        }`}
      >
        {/* TopBar Superior */}
        <TopBar
          activeView={activeView}
          selectedDimension={selectedDimension}
          userRole={userRole}
          onToggleRole={handleToggleRole}
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          latestPeriod={metadata?.periods.latest}
          dataAsOf={metadata?.data_as_of}
          onExportReport={isAuthenticated ? handleExportGlobal : undefined}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed((prev) => !prev)}
        />

        {/* Área de Visualización */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 w-full space-y-6">
          {activeView === "dashboard" && (
            <DashboardView
              metadata={metadata}
              selectedIndicator={selectedIndicator}
              onSelectIndicator={setSelectedIndicator}
              kpiValues={kpiValues}
              level={level}
              onLevelChange={setLevel}
              selectedSegments={selectedSegments}
              onToggleSegment={handleToggleSegment}
              selectedProvince={selectedProvince}
              onProvinceChange={setSelectedProvince}
              fromPeriod={fromPeriod}
              toPeriod={toPeriod}
              onFromChange={setFromPeriod}
              onToChange={setToPeriod}
              selectedRucs={selectedRucs}
              onRemoveRuc={handleRemoveRuc}
              seriesData={seriesData}
              loadingSeries={loadingSeries}
              seriesError={seriesError}
              entities={entities}
              onNavigateToBenchmarking={() => setActiveView("benchmarking")}
              selectedDimension={selectedDimension}
              userRole={userRole}
              onUnlockAccredited={openLoginModal}
            />
          )}

          {activeView === "benchmarking" && (
            <ProtectedRoute
              requiredRoles={["investigador", "auditor", "administrador"]}
              fallbackTitle="Supervisión & Benchmarking Multi-Entidad CAMEL"
              fallbackDescription="El comparador analítico de hasta 5 cooperativas simultáneas con semáforo normativo SEPS v3.0 y exportación en streaming requiere credenciales institucionales de la Capa Pro."
            >
              <BenchmarkingProView
                metadata={metadata}
                entities={entities}
                initialSelectedRucs={selectedRucs}
              />
            </ProtectedRoute>
          )}

          {activeView === "catalog" && (
            <CatalogView
              userRole={userRole}
              onSelectAndGraph={handleSelectAndGraph}
              onUnlockAccredited={openLoginModal}
            />
          )}

          {activeView === "entities" && (
            <EntitiesView
              entities={entities}
              isLoading={loadingEntities}
              searchQuery={searchQuery}
              onSearchChange={(q) => {
                setSearchQuery(q)
                setEntityPage(1)
              }}
              selectedRucs={selectedRucs}
              onToggleEntity={handleToggleEntity}
              currentPage={entityPage}
              totalPages={entityTotalPages}
              totalItems={entityTotalItems}
              onPageChange={setEntityPage}
              onNavigateToBenchmarking={() => setActiveView("benchmarking")}
              onNavigateToDashboard={() => {
                setActiveView("dashboard")
                setSelectedDimension("all")
              }}
              canExport={isAuthenticated}
            />
          )}

          {activeView === "admin_users" && (
            <ProtectedRoute
              requiredRoles={["administrador"]}
              fallbackTitle="Panel de Administración Exclusivo"
              fallbackDescription="La gestión del padrón de usuarios institucionales está restringida exclusivamente a usuarios con rol de Administrador."
            >
              <AdminUsersView />
            </ProtectedRoute>
          )}
        </main>

        {/* Footer Institucional */}
        <footer className="border-t border-slate-200/80 bg-white py-5 px-6 lg:px-8 text-xs text-slate-500 mt-auto w-full">
          <div className="w-full flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800">ESPOCH - DI - 060</span>
              <span>•</span>
              <span>Sistema de Indicadores SFPS</span>
              <span>•</span>
              <span>Capa Pro (DuckDB + Supabase + RBAC)</span>
            </div>
            <div className="font-mono text-[11px] text-slate-400">
              Dirección de Investigación ESPOCH • Fichas Metodológicas SEPS V3.0
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App
