import React from "react"
import { Building2, ShieldCheck, Database, Calendar } from "lucide-react"
import { Badge } from "@/components/ui/badge"

interface HeaderProps {
  dataAsOf?: string
}

export const Header: React.FC<HeaderProps> = ({ dataAsOf = "2025-12-31" }) => {
  return (
    <header className="border-b border-emerald-950/10 bg-white/80 backdrop-blur-md sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-800 flex items-center justify-center text-white shadow-md shadow-emerald-900/15">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-slate-900 tracking-tight">
                Sistema de Indicadores Financieros SFPS
              </h1>
              <Badge variant="mint" className="hidden sm:inline-flex text-[10px]">
                SEPS B11
              </Badge>
            </div>
            <p className="text-xs text-slate-500 font-medium">
              Plataforma Analítica del Sector Cooperativo del Ecuador
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-lg bg-emerald-50/70 border border-emerald-200/50 text-xs text-emerald-900 font-medium">
            <Calendar className="h-3.5 w-3.5 text-emerald-700" />
            <span>Corte: {dataAsOf}</span>
          </div>

          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200/60 text-xs text-slate-700">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-[11px] font-semibold">SDD OpenAPI 3.1</span>
          </div>
        </div>
      </div>
    </header>
  )
}
