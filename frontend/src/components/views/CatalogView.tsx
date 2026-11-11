import React, { useState, useMemo } from "react"
import {
  BookOpen,
  Search,
  ArrowRight
} from "lucide-react"
import {
  EXTENDED_CATALOG,
  CATEGORY_LABELS,
  type CatalogIndicator,
  type IndicatorCategory
} from "@/data/extendedCatalog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import type { UserRole } from "@/components/Sidebar"

interface CatalogViewProps {
  userRole: UserRole
  onSelectAndGraph: (indicatorId: string) => void
  onUnlockAccredited: () => void
}

export const CatalogView: React.FC<CatalogViewProps> = ({
  userRole,
  onSelectAndGraph,
  onUnlockAccredited
}) => {
  const isAccredited = userRole === "accredited"

  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [selectedAccess, setSelectedAccess] = useState<string>("all")
  const [searchQuery, setSearchQuery] = useState<string>("")

  // En modo público: Al menos 4 de cada tipo (23 indicadores públicos en total)
  const baseIndicators = useMemo(() => {
    return isAccredited
      ? EXTENDED_CATALOG
      : EXTENDED_CATALOG.filter((i) => i.access === "public")
  }, [isAccredited])

  // Filtrado de indicadores
  const filteredIndicators = useMemo(() => {
    return baseIndicators.filter((ind) => {
      // Filtro de categoría
      if (selectedCategory !== "all" && ind.category !== selectedCategory) {
        return false
      }
      // Filtro de acceso (solo si es acreditado)
      if (isAccredited) {
        if (selectedAccess === "public" && ind.access !== "public") {
          return false
        }
        if (selectedAccess === "accredited" && ind.access !== "accredited") {
          return false
        }
      }
      // Búsqueda por texto
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const matchName = ind.name.toLowerCase().includes(q)
        const matchShort = ind.short_name.toLowerCase().includes(q)
        const matchDesc = ind.description.toLowerCase().includes(q)
        const matchFicha = `ficha ${ind.seps_ficha_number}`.includes(q)
        if (!matchName && !matchShort && !matchDesc && !matchFicha) {
          return false
        }
      }
      return true
    })
  }, [baseIndicators, selectedCategory, selectedAccess, searchQuery, isAccredited])

  const totalPublic = EXTENDED_CATALOG.filter((i) => i.access === "public").length
  const totalAccredited = EXTENDED_CATALOG.filter((i) => i.access === "accredited").length

  return (
    <div className="space-y-6 w-full">
      {/* Cabecera Informativa */}
      <div className="rounded-2xl border border-emerald-200/90 bg-gradient-to-r from-emerald-50 via-teal-50/50 to-white p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-emerald-600 text-white shadow-xs">
                <BookOpen className="h-4 w-4" />
              </span>
              <h2 className="text-lg font-bold text-slate-900 font-serif">
                Catálogo de Indicadores Financieros SEPS V3.0
              </h2>
            </div>
            <p className="text-xs text-slate-600 max-w-3xl leading-relaxed">
              Basado en las Fichas Metodológicas oficiales emitidas por la Superintendencia de Economía Popular y
              Solidaria. Todos los indicadores se calculan directamente sobre la estructura contable B11.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="mint" className="text-xs px-2.5 py-1">
              {filteredIndicators.length} Indicadores Oficiales
            </Badge>
            {isAccredited && (
              <Badge variant="gold" className="text-xs px-2.5 py-1">
                Fichas Acreditadas ({totalAccredited})
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Barra de Filtros y Búsqueda */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          {/* Buscador */}
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Buscar por nombre, ficha (ej. Ficha 5), o descripción..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 text-xs h-9 bg-slate-50/60"
            />
          </div>

          {/* Filtro de Acceso (Únicamente visible en Modo Acreditado) */}
          {isAccredited && (
            <div className="flex items-center gap-1.5 w-full md:w-auto">
              <span className="text-xs text-slate-400 font-medium mr-1 hidden sm:inline">
                Acceso:
              </span>
              <button
                type="button"
                onClick={() => setSelectedAccess("all")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedAccess === "all"
                    ? "bg-slate-800 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Todos ({EXTENDED_CATALOG.length})
              </button>
              <button
                type="button"
                onClick={() => setSelectedAccess("public")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedAccess === "public"
                    ? "bg-emerald-600 text-white"
                    : "bg-emerald-50 text-emerald-800 hover:bg-emerald-100"
                }`}
              >
                Públicos ({totalPublic})
              </button>
              <button
                type="button"
                onClick={() => setSelectedAccess("accredited")}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedAccess === "accredited"
                    ? "bg-amber-500 text-white"
                    : "bg-amber-50 text-amber-800 hover:bg-amber-100"
                }`}
              >
                Acreditados ({totalAccredited})
              </button>
            </div>
          )}
        </div>

        {/* Pestañas de Categoría */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100">
          <button
            type="button"
            onClick={() => setSelectedCategory("all")}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              selectedCategory === "all"
                ? "bg-emerald-100 text-emerald-900 font-bold"
                : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
            }`}
          >
            Todas las Dimensiones
          </button>
          {Object.entries(CATEGORY_LABELS).map(([catKey, catMeta]) => {
            const isSelected = selectedCategory === catKey
            return (
              <button
                key={catKey}
                type="button"
                onClick={() => setSelectedCategory(catKey)}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  isSelected
                    ? "bg-emerald-100 text-emerald-900 font-bold"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                }`}
              >
                {catMeta.name}
              </button>
            )
          })}
        </div>
      </div>

      {/* Grid de Tarjetas de Indicadores */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredIndicators.map((ind) => {
          const catMeta = CATEGORY_LABELS[ind.category]

          return (
            <Card
              key={ind.id}
              className={`border transition-all hover:shadow-md ${
                ind.is_live
                  ? "border-emerald-200/90 bg-white"
                  : "border-slate-200/80 bg-slate-50/40"
              }`}
            >
              <CardHeader className="p-4 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 bg-emerald-100/80 px-2 py-0.5 rounded-md font-mono">
                        Ficha #{ind.seps_ficha_number}
                      </span>
                      <span className="text-[11px] text-slate-400 capitalize">
                        {catMeta?.name}
                      </span>
                    </div>

                    <CardTitle className="text-sm font-bold text-slate-900 leading-snug">
                      {ind.name}
                    </CardTitle>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {ind.is_live && (
                      <Badge variant="mint" className="text-[10px]">
                        Disponible
                      </Badge>
                    )}
                  </div>
                </div>

                <CardDescription className="text-xs text-slate-600 line-clamp-2 pt-1">
                  {ind.description}
                </CardDescription>
              </CardHeader>

              <CardContent className="p-4 pt-2 space-y-3">
                {/* Caja de Fórmula Matemática */}
                <div className="rounded-lg bg-slate-900 text-slate-100 p-2.5 font-mono text-[11px] border border-slate-800 shadow-inner">
                  <div className="text-[10px] text-slate-400 uppercase tracking-wider font-sans font-semibold mb-1">
                    Fórmula Normativa SEPS:
                  </div>
                  <div className="text-emerald-300 font-semibold">{ind.formula_display}</div>
                  <div className="text-[10px] text-slate-400 mt-1 font-sans">
                    Cuentas B11: {ind.components_description}
                  </div>
                </div>

                {/* Umbrales y Acciones */}
                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                  <div className="text-[11px] text-slate-500">
                    <span className="font-semibold text-slate-700">Norma:</span>{" "}
                    {ind.regulatory_threshold || "Referencial"}
                  </div>

                  {ind.is_live && (
                    <Button
                      variant="fintech"
                      size="sm"
                      onClick={() => onSelectAndGraph(ind.id)}
                      className="text-xs h-7 px-3 gap-1 shadow-2xs"
                    >
                      <span>Graficar en Dashboard</span>
                      <ArrowRight className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
