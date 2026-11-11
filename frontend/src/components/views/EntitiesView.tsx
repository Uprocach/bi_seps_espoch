import React from "react"
import { Building2, ArrowRight, ShieldCheck, Scale, FileSpreadsheet } from "lucide-react"
import { EntityTable } from "@/components/EntityTable"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { EntitySummary } from "@/services/apiClient"

interface EntitiesViewProps {
  entities: EntitySummary[]
  isLoading: boolean
  searchQuery: string
  onSearchChange: (q: string) => void
  selectedRucs: string[]
  onToggleEntity: (ruc: string) => void
  currentPage: number
  totalPages: number
  totalItems: number
  onPageChange: (page: number) => void
  onNavigateToBenchmarking: () => void
  onNavigateToDashboard: () => void
  canExport?: boolean
}

export const EntitiesView: React.FC<EntitiesViewProps> = ({
  entities,
  isLoading,
  searchQuery,
  onSearchChange,
  selectedRucs,
  onToggleEntity,
  currentPage,
  totalPages,
  totalItems,
  onPageChange,
  onNavigateToBenchmarking,
  onNavigateToDashboard,
  canExport = false
}) => {
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
            <Badge variant="mint" className="text-[10px] uppercase font-bold">
              Segmentos 1 y 2
            </Badge>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed max-w-3xl">
            Entidades supervisadas por la SEPS. Selecciona cooperativas para contrastar y visualizar sus series de tiempo en el panel analítico.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {selectedRucs.length > 0 && (
            <Button
              variant="default"
              size="sm"
              onClick={onNavigateToDashboard}
              className="text-xs h-8 font-semibold gap-1.5 bg-emerald-700 hover:bg-emerald-800 text-white shadow-2xs"
            >
              <span>Ver en Gráfico ({selectedRucs.length})</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          )}

          {canExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={onNavigateToBenchmarking}
              className="text-xs h-8 font-semibold gap-1.5 text-emerald-800 border-emerald-300 hover:bg-emerald-50 shadow-2xs"
            >
              <Scale className="h-3.5 w-3.5" />
              <span>Diagnóstico CAMEL</span>
            </Button>
          )}
        </div>
      </div>

      {/* Tabla de Entidades con buscador y paginación */}
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
        canExport={canExport}
      />
    </div>
  )
}
