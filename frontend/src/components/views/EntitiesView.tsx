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
      {/* Banner Superior del Directorio */}
      <div className="rounded-2xl border border-slate-200/90 bg-gradient-to-r from-slate-900 to-slate-800 text-white p-6 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <Building2 className="h-4 w-4" />
            </span>
            <h2 className="text-lg font-bold font-serif text-white">
              Padrón de Cooperativas de Ahorro y Crédito Supervisadas
            </h2>
          </div>
          <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
            Consorcio de entidades clasificadas en Segmentos 1 y 2 por la SEPS. Selecciona cooperativas
            para analizar sus series temporales en el panel analítico{canExport ? " o auditarlas en el módulo de Diagnóstico CAMEL." : "."}
          </p>
        </div>

        {canExport && (
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="secondary"
              size="sm"
              onClick={onNavigateToBenchmarking}
              className="text-xs h-9 font-semibold gap-1.5 bg-emerald-500 hover:bg-emerald-400 text-white shadow-sm"
            >
              <Scale className="h-3.5 w-3.5" />
              <span>Diagnóstico CAMEL</span>
            </Button>
          </div>
        )}
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
