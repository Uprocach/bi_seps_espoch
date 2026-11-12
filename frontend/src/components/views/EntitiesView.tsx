import React from "react"
import { Building2, ArrowRight, ShieldCheck, Scale, FileSpreadsheet } from "lucide-react"
import { EntityTable } from "@/components/EntityTable"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { EntitySummary } from "@/services/httpClient"
import { useDashboardStore } from "@/store/useDashboardStore"
import { useAuthStore } from "@/store/useAuthStore"
import { useEntitiesQuery } from "@/hooks/useIndicatorsQueries"

interface EntitiesViewProps {
  entities?: EntitySummary[]
  isLoading?: boolean
  searchQuery?: string
  onSearchChange?: (q: string) => void
  selectedRucs?: string[]
  onToggleEntity?: (ruc: string) => void
  currentPage?: number
  totalPages?: number
  totalItems?: number
  onPageChange?: (page: number) => void
  onNavigateToBenchmarking?: () => void
  onNavigateToDashboard?: () => void
  canExport?: boolean
}

export const EntitiesView: React.FC<EntitiesViewProps> = (props) => {
  const store = useDashboardStore()
  const { isAuthenticated } = useAuthStore()

  const searchQuery = props.searchQuery !== undefined ? props.searchQuery : store.searchQuery
  const currentPage = props.currentPage !== undefined ? props.currentPage : store.entityPage
  const selectedRucs = props.selectedRucs !== undefined ? props.selectedRucs : store.selectedRucs
  const canExport = props.canExport !== undefined ? props.canExport : isAuthenticated

  const { data: entitiesData, isLoading: loadingQuery } = useEntitiesQuery({
    q: searchQuery || undefined,
    province: store.selectedProvince ? [store.selectedProvince] : undefined,
    segment: store.level === "segment" ? store.selectedSegments : undefined,
    page: currentPage,
    pageSize: 15
  })

  const entities = props.entities !== undefined ? props.entities : (entitiesData?.data || [])
  const isLoading = props.isLoading !== undefined ? props.isLoading : loadingQuery
  const totalPages = props.totalPages !== undefined ? props.totalPages : (entitiesData?.pagination.total_pages || 1)
  const totalItems = props.totalItems !== undefined ? props.totalItems : (entitiesData?.pagination.total_items || 0)

  const onSearchChange = props.onSearchChange ?? store.setSearchQuery
  const onPageChange = props.onPageChange ?? store.setEntityPage
  const onToggleEntity = props.onToggleEntity ?? store.toggleRuc
  const onNavigateToBenchmarking = props.onNavigateToBenchmarking ?? (() => store.setActiveView("benchmarking"))
  const onNavigateToDashboard = props.onNavigateToDashboard ?? (() => {
    store.setActiveView("dashboard")
    store.setSelectedDimension("all")
    if (selectedRucs.length > 0) {
      store.setLevel("entity")
    }
  })

  return (
    <div className="space-y-6">
      {/* Cabecera Minimalista del Directorio */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200/80">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200/80 shadow-2xs">
              <Building2 className="h-4 w-4" />
            </span>
            <h2 className="text-base sm:text-lg font-bold font-serif tracking-tight text-slate-900">
              Padrón de Cooperativas Supervisadas
            </h2>
            <Badge variant="mint" className="text-[10px] font-mono">
              SEPS
            </Badge>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed max-w-4xl">
            Directorio institucional de Cooperativas de Ahorro y Crédito y Asociaciones Mutualistas pertenecientes a los Segmentos 1 y 2 con estados financieros reportados a la SEPS.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Badge variant="outline" className="text-xs font-mono px-2.5 py-1 bg-white border-slate-200 text-slate-700">
            {totalItems} Entidades
          </Badge>
          {canExport && (
            <Badge variant="mint" className="text-xs px-2.5 py-1">
              Exportación Autorizada
            </Badge>
          )}
        </div>
      </div>

      {/* Banner de Cooperativas Seleccionadas para Análisis */}
      {selectedRucs.length > 0 && (
        <Card className="border-emerald-200/80 bg-emerald-50/20 shadow-xs">
          <CardContent className="py-3 px-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse" />
              <span className="text-xs font-semibold text-emerald-950 font-serif">
                {selectedRucs.length} cooperativa{selectedRucs.length > 1 ? "s" : ""} seleccionada{selectedRucs.length > 1 ? "s" : ""} para análisis
              </span>
              <span className="text-xs text-emerald-800/80 font-mono text-[11px]">
                (Máximo 5 permitidas)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onNavigateToDashboard}
                className="text-xs border-emerald-600/30 text-emerald-800 hover:bg-emerald-100/50"
              >
                Graficar en Dashboard
              </Button>
              <Button
                size="sm"
                onClick={onNavigateToBenchmarking}
                className="text-xs bg-emerald-700 hover:bg-emerald-800 text-white font-medium shadow-2xs"
              >
                <Scale className="h-3.5 w-3.5 mr-1" />
                Diagnóstico CAMEL
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabla Principal de Entidades */}
      <EntityTable
        entities={entities}
        isLoading={isLoading}
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
        selectedRucs={selectedRucs}
        onToggleEntity={onToggleEntity}
        currentPage={currentPage}
        totalPages={totalPages}
        totalItems={totalItems}
        onPageChange={onPageChange}
      />
    </div>
  )
}
export default EntitiesView
