import React from "react"
import { Filter, Layers, Globe, Building } from "lucide-react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import type { Segment, Province, AggregationLevel, SegmentCode } from "@/services/apiClient"

interface FiltersBarProps {
  level: AggregationLevel
  onLevelChange: (lvl: AggregationLevel) => void
  segments: Segment[]
  selectedSegments: SegmentCode[]
  onToggleSegment: (seg: SegmentCode) => void
  provinces: Province[]
  selectedProvince: string
  onProvinceChange: (prov: string) => void
  periods: string[]
  fromPeriod: string
  toPeriod: string
  onFromChange: (p: string) => void
  onToChange: (p: string) => void
}

export const FiltersBar: React.FC<FiltersBarProps> = ({
  level,
  onLevelChange,
  segments,
  selectedSegments,
  onToggleSegment,
  provinces,
  selectedProvince,
  onProvinceChange,
  periods,
  fromPeriod,
  toPeriod,
  onFromChange,
  onToChange
}) => {
  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-sm flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
      {/* Selector de Nivel */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 w-full lg:w-auto">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-emerald-700" /> Nivel:
        </span>
        <Tabs value={level} onValueChange={(v) => onLevelChange(v as AggregationLevel)} className="w-full sm:w-auto">
          <TabsList className="grid grid-cols-3 w-full sm:w-auto h-8 bg-slate-100 p-0.5">
            <TabsTrigger value="country" className="text-xs px-3 py-1 flex items-center gap-1">
              <Globe className="h-3 w-3" /> Sistema
            </TabsTrigger>
            <TabsTrigger value="segment" className="text-xs px-3 py-1 flex items-center gap-1">
              <Layers className="h-3 w-3" /> Segmentos
            </TabsTrigger>
            <TabsTrigger value="entity" className="text-xs px-3 py-1 flex items-center gap-1">
              <Building className="h-3 w-3" /> Cooperativas
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Filtros dinámicos según el nivel */}
      <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto justify-start lg:justify-end">
        {level === "segment" && (
          <div className="flex flex-wrap items-center gap-1.5">
            {segments.map((s) => {
              const isChecked = selectedSegments.includes(s.code)
              return (
                <button
                  key={s.code}
                  type="button"
                  onClick={() => onToggleSegment(s.code)}
                  className={`text-xs px-2.5 py-1 rounded-md border font-medium transition-colors ${
                    isChecked
                      ? "bg-emerald-700 text-white border-emerald-700 shadow-sm"
                      : "bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  {s.label.replace("Segmento ", "Seg ")}
                </button>
              )
            })}
          </div>
        )}

        {/* Filtro Provincia */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="province-select" className="text-xs text-slate-500 font-medium">Provincia:</label>
          <select
            id="province-select"
            value={selectedProvince}
            onChange={(e) => onProvinceChange(e.target.value)}
            className="text-xs h-8 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-slate-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-600"
          >
            <option value="">Todas ({provinces.length})</option>
            {provinces.map((p) => (
              <option key={p.code} value={p.code}>
                {p.name} {p.entity_count ? `(${p.entity_count})` : ""}
              </option>
            ))}
          </select>
        </div>

        {/* Rango de Periodos */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="period-from" className="text-xs text-slate-500 font-medium">Periodo:</label>
          <select
            id="period-from"
            value={fromPeriod}
            onChange={(e) => onFromChange(e.target.value)}
            className="text-xs h-8 rounded-lg border border-slate-200 bg-white px-2 py-1 text-slate-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-600"
          >
            {periods.map((p) => (
              <option key={`from-${p}`} value={p}>
                {p}
              </option>
            ))}
          </select>
          <span className="text-xs text-slate-400 font-medium">-</span>
          <select
            id="period-to"
            value={toPeriod}
            onChange={(e) => onToChange(e.target.value)}
            className="text-xs h-8 rounded-lg border border-slate-200 bg-white px-2 py-1 text-slate-800 shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-600"
          >
            {periods.map((p) => (
              <option key={`to-${p}`} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}
