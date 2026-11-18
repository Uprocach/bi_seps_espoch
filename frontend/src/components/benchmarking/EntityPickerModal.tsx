import React from "react"
import { Building2, Check, Plus, Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { EntitySummary } from "@/services/httpClient"
import type { SegmentCounts } from "@/lib/benchmarkingModel"
import { formatCoopName } from "@/lib/utils"

interface EntityPickerModalProps {
  isOpen: boolean
  onClose: () => void
  fullEntityCatalog: EntitySummary[]
  filteredCandidates: EntitySummary[]
  selectedRucs: string[]
  searchFilter: string
  onSearchFilterChange: (val: string) => void
  pickerSegmentFilter: string
  onPickerSegmentFilterChange: (seg: string) => void
  pickerSort: "assets" | "name"
  onPickerSortChange: (sort: "assets" | "name") => void
  segmentCounts: SegmentCounts
  onAddEntity: (ruc: string) => void
}

export const EntityPickerModal: React.FC<EntityPickerModalProps> = ({
  isOpen,
  onClose,
  fullEntityCatalog,
  filteredCandidates,
  selectedRucs,
  searchFilter,
  onSearchFilterChange,
  pickerSegmentFilter,
  onPickerSegmentFilterChange,
  pickerSort,
  onPickerSortChange,
  segmentCounts,
  onAddEntity
}) => {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-2xl w-full flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
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
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 border-b border-slate-100 space-y-3 bg-white">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por nombre comercial, razón social o RUC (ej. Chibuleo, Mushuc Runa, Jardín Azuayo, 29 de Octubre)..."
              value={searchFilter}
              onChange={(e) => onSearchFilterChange(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:bg-white text-slate-900 font-medium"
              autoFocus
            />
            {searchFilter && (
              <button
                onClick={() => onSearchFilterChange("")}
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
                  onClick={() => onPickerSegmentFilterChange(seg.id)}
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
                onClick={() => onPickerSortChange("assets")}
                className={`px-2 py-0.5 rounded border transition-colors ${
                  pickerSort === "assets"
                    ? "bg-slate-800 text-white border-slate-800 font-bold"
                    : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                }`}
              >
                Por Activos
              </button>
              <button
                onClick={() => onPickerSortChange("name")}
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
                cand.segment === "SEGMENTO_1_MUTUALISTA"
                  ? "Mutualista"
                  : cand.segment.replace("SEGMENTO_", "Segmento ")

              const assetsStr = cand.total_assets_usd
                ? `$${(cand.total_assets_usd / 1_000_000).toFixed(1)}M`
                : "Sin dato"

              return (
                <div
                  key={cand.ruc}
                  className="p-3 hover:bg-emerald-50/50 rounded-xl transition-colors flex items-center justify-between gap-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-slate-900 text-xs truncate" title={cand.razon_social}>
                        {cleanName}
                      </p>
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700">
                        {segLabel}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate mt-0.5 flex items-center gap-2">
                      <span className="font-mono text-slate-500">RUC: {cand.ruc}</span>
                      <span>•</span>
                      <span>{cand.province?.name || "Ecuador"}</span>
                      <span>•</span>
                      <span>
                        Activos: <strong className="text-slate-600 font-mono">{assetsStr}</strong>
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
                      onClick={() => onAddEntity(cand.ruc)}
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

        <div className="p-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-xs text-slate-500">
          <span>
            Mostrando <strong className="text-slate-700">{filteredCandidates.length}</strong> de{" "}
            <strong className="text-slate-700">{fullEntityCatalog.length}</strong> cooperativas (
            {selectedRucs.length}/5 seleccionadas)
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            className="text-xs h-7 border-slate-200 hover:bg-slate-100"
          >
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  )
}
