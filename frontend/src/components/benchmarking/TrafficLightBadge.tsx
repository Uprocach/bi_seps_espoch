import React from "react"
import { CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react"
import type { CamelEvaluation, TrafficLightStatus } from "@/types/camel"
import { formatIndicatorValue } from "@/lib/utils"
import { resolveNeutralTrafficLightLabel } from "@/lib/benchmarkingModel"

interface TrafficLightBadgeProps {
  evalItem: CamelEvaluation | undefined
  value: number | null
  unit: string
  size?: "sm" | "md"
}

export const TrafficLightBadge: React.FC<TrafficLightBadgeProps> = ({
  evalItem,
  value,
  unit,
  size = "sm"
}) => {
  const neutralLabel = resolveNeutralTrafficLightLabel(value)
  if (!evalItem || neutralLabel) {
    return (
      <span
        title={evalItem?.message || "Dato no reportado o base contable insuficiente en el periodo."}
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-500 border border-slate-200/80"
      >
        {neutralLabel ?? "Sin dato"}
      </span>
    )
  }

  const st: TrafficLightStatus = evalItem.status
  let badgeClasses = ""
  let Icon = CheckCircle2
  let label = "Cumple"

  if (st === "GREEN") {
    badgeClasses = "bg-emerald-50 text-emerald-800 border-emerald-300"
    Icon = CheckCircle2
    label = "Óptimo"
  } else if (st === "YELLOW") {
    badgeClasses = "bg-amber-50 text-amber-800 border-amber-300"
    Icon = AlertTriangle
    label = "Alerta"
  } else {
    badgeClasses = "bg-rose-50 text-rose-800 border-rose-300"
    Icon = ShieldAlert
    label = "Crítico"
  }

  const formattedValue = formatIndicatorValue(value, unit)

  return (
    <div className="group relative inline-flex items-center">
      <span
        className={`inline-flex items-center gap-1.5 rounded-md font-semibold border shadow-xs transition-all cursor-help ${
          size === "md" ? "px-3 py-1.5 text-xs" : "px-2.5 py-1 text-xs"
        } ${badgeClasses}`}
      >
        <Icon className="w-3.5 h-3.5 flex-shrink-0" />
        <span>{formattedValue}</span>
        {size === "md" && (
          <span className="text-[10px] uppercase font-bold tracking-wider ml-1 opacity-80">
            ({label})
          </span>
        )}
      </span>

      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-30 w-64 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-xl pointer-events-none leading-snug">
        <p className="font-bold text-amber-300 mb-0.5">
          {evalItem.normative_reference || "Normativa SEPS / COMF"}
        </p>
        <p className="text-slate-200">{evalItem.message}</p>
        <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
      </div>
    </div>
  )
}
