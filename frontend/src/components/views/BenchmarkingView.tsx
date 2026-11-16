import React from "react"
import {
  BarChart3,
  Building2,
  FileSpreadsheet,
  FileText,
  Info,
  Loader2,
  Plus,
  Trophy,
  X
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { EntitySummary, FiltersMetadata } from "@/services/httpClient"
import { useAuthStore } from "@/store/useAuthStore"
import { useBenchmarkingWorkbench } from "@/hooks/useBenchmarkingWorkbench"
import { ENTITY_PALETTE, PRO_TABS, type ProTabId } from "@/lib/benchmarkingModel"
import { formatCoopName } from "@/lib/utils"
import { EntityPickerModal } from "@/components/benchmarking/EntityPickerModal"
import { RankingPanel } from "@/components/benchmarking/RankingPanel"
import { CamelDimensionPanel } from "@/components/benchmarking/CamelDimensionPanel"

export type { ProTabId }

interface BenchmarkingProViewProps {
  metadata?: FiltersMetadata | null
  entities?: EntitySummary[]
  initialSelectedRucs?: string[]
}

export const BenchmarkingProView: React.FC<BenchmarkingProViewProps> = (props) => {
  const { user } = useAuthStore()
  const workbench = useBenchmarkingWorkbench(props)

  const {
    selectedRucs,
    activeTab,
    setActiveTab,
    isEntityPickerOpen,
    setIsEntityPickerOpen,
    searchFilter,
    setSearchFilter,
    pickerSegmentFilter,
    setPickerSegmentFilter,
    pickerSort,
    setPickerSort,
    fullEntityCatalog,
    segmentCounts,
    filteredCandidates,
    isLoadingBenchmark,
    isExportingCsv,
    isExportingExcel,
    exportMessage,
    clearExportMessage,
    handleAddEntity,
    handleRemoveEntity,
    handleExportCsv,
    handleExportExcel
  } = workbench

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
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
            Benchmarking Multi-Entidad &amp; Dashboard CAMEL
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Supervisión analítica de cooperativas contrastadas contra las líneas base del Segmento 1 y la media nacional (SEPS v3.0).
          </p>
        </div>

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

      {exportMessage && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>{exportMessage}</span>
          </div>
          <button
            onClick={clearExportMessage}
            className="text-amber-500 hover:text-amber-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

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

        <EntityPickerModal
          isOpen={isEntityPickerOpen}
          onClose={() => setIsEntityPickerOpen(false)}
          fullEntityCatalog={fullEntityCatalog}
          filteredCandidates={filteredCandidates}
          selectedRucs={selectedRucs}
          searchFilter={searchFilter}
          onSearchFilterChange={setSearchFilter}
          pickerSegmentFilter={pickerSegmentFilter}
          onPickerSegmentFilterChange={setPickerSegmentFilter}
          pickerSort={pickerSort}
          onPickerSortChange={setPickerSort}
          segmentCounts={segmentCounts}
          onAddEntity={handleAddEntity}
        />

        <div className="flex flex-wrap items-center gap-2">
          {selectedRucs.map((ruc, idx) => {
            const ent = fullEntityCatalog.find((e) => e.ruc === ruc) || {
              ruc,
              razon_social: ruc
            }
            const cleanName = formatCoopName(ent.razon_social)
            const color = ENTITY_PALETTE[idx % ENTITY_PALETTE.length]
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

      {activeTab === "ranking" ? (
        <RankingPanel workbench={workbench} />
      ) : (
        <CamelDimensionPanel workbench={workbench} />
      )}
    </div>
  )
}

export const BenchmarkingView = BenchmarkingProView
export type BenchmarkingViewProps = BenchmarkingProViewProps
export default BenchmarkingView
