import React from "react"
import {
  AlertCircle,
  Award,
  TrendingUp,
  Percent,
  Settings,
  ShieldAlert
} from "lucide-react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { IndicatorMeta } from "@/services/apiClient"

export interface KPIValues {
  [indicatorId: string]: {
    value: number | null
    prevValue?: number | null
    numerator?: number | null
    denominator?: number | null
  }
}

export const CORE_5_INDICATORS = [
  {
    id: "morosidad_cartera_total",
    dimension: "1. Calidad de Activos",
    shortName: "Morosidad de Cartera",
    icon: AlertCircle,
    colorClass: "text-amber-600 bg-amber-50"
  },
  {
    id: "solvencia_patrimonial",
    dimension: "2. Capital & Solvencia",
    shortName: "Solvencia Patrimonial",
    icon: Award,
    colorClass: "text-emerald-700 bg-emerald-50"
  },
  {
    id: "roa",
    dimension: "3. Rentabilidad",
    shortName: "Rentabilidad (ROA)",
    icon: TrendingUp,
    colorClass: "text-teal-600 bg-teal-50"
  },
  {
    id: "liquidez_inmediata",
    dimension: "4. Liquidez",
    shortName: "Liquidez Inmediata",
    icon: Percent,
    colorClass: "text-cyan-600 bg-cyan-50"
  },
  {
    id: "eficiencia_operativa",
    dimension: "5. Eficiencia & Gestión",
    shortName: "Eficiencia Operativa",
    icon: Settings,
    colorClass: "text-slate-700 bg-slate-100"
  }
]

interface KPICardsProps {
  indicators: IndicatorMeta[]
  selectedIndicator: string
  onSelectIndicator: (id: string) => void
  kpiValues: KPIValues
  periodLabel?: string
}

export const KPICards: React.FC<KPICardsProps> = ({
  indicators,
  selectedIndicator,
  onSelectIndicator,
  kpiValues,
  periodLabel = "2025-12"
}) => {
  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse" />
          <h2 className="text-xs sm:text-sm font-bold text-slate-800 tracking-tight uppercase">
            5 Indicadores Clave del SFPS (Metodología CAMEL)
          </h2>
          <Badge variant="mint" className="text-[10px] hidden sm:inline-flex">
            Corte {periodLabel}
          </Badge>
        </div>
        <span className="text-[11px] text-slate-400 font-medium hidden md:inline">
          Haz clic en cualquier tarjeta para proyectar su evolución en la gráfica
        </span>
      </div>

      {/* Grid de 5 indicadores fijos (1 por grupo CAMEL) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
        {CORE_5_INDICATORS.map((core) => {
          const currentMeta = indicators.find((i) => i.id === core.id)
          const isSelectedInChart = selectedIndicator === core.id
          const val = kpiValues[core.id]?.value
          const Icon = core.icon
          const isLowerBetter = currentMeta?.polarity === "lower_is_better"

          return (
            <Card
              key={core.id}
              onClick={() => onSelectIndicator(core.id)}
              className={cn(
                "cursor-pointer transition-all duration-200 relative overflow-hidden group bg-white shadow-2xs hover:shadow-md border",
                isSelectedInChart
                  ? "border-emerald-600 bg-gradient-to-b from-emerald-50/50 via-white to-white ring-2 ring-emerald-600/20 shadow-sm"
                  : "border-slate-200/90 hover:border-emerald-300"
              )}
            >
              {isSelectedInChart && (
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-600 via-teal-500 to-amber-500" />
              )}

              <CardHeader className="p-3.5 pb-1 space-y-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono truncate">
                    {core.dimension}
                  </span>
                  <div className={cn("p-1.5 rounded-lg shrink-0", core.colorClass)}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <CardTitle className="text-xs font-bold text-slate-900 truncate">
                    {core.shortName}
                  </CardTitle>
                  {isSelectedInChart && (
                    <Badge variant="mint" className="text-[9px] px-1.5 py-0 h-4 uppercase font-bold shrink-0">
                      En Gráfico
                    </Badge>
                  )}
                </div>
              </CardHeader>

              <CardContent className="p-3.5 pt-2">
                <div className="flex items-baseline justify-between mb-1.5">
                  <div className="text-2xl font-bold tracking-tight text-slate-900 font-mono">
                    {val !== null && val !== undefined
                      ? `${val.toFixed(currentMeta?.decimals ?? 2)}%`
                      : "Cargando..."}
                  </div>
                  <Badge
                    variant={isLowerBetter ? "gold" : "mint"}
                    className="text-[10px] font-semibold"
                  >
                    {isLowerBetter ? "Menor es mejor" : "Mayor es mejor"}
                  </Badge>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100">
                  <span className="truncate max-w-[140px] text-[10px] text-slate-500">
                    {currentMeta?.name || core.shortName}
                  </span>
                  <span className="font-mono text-slate-400 font-medium text-[10px]">
                    {periodLabel}
                  </span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
