import React from "react"
import { Menu, ShieldCheck, Users, Calendar, Download, LogIn, LogOut } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { ActiveView, UserRole } from "@/components/Sidebar"
import { CAMEL_DIMENSIONS, type IndicatorCategory } from "@/data/extendedCatalog"

interface TopBarProps {
  activeView: ActiveView
  selectedDimension?: "all" | IndicatorCategory
  userRole: UserRole
  onToggleRole: () => void
  onOpenMobileMenu: () => void
  latestPeriod?: string
  dataAsOf?: string
  onExportReport?: () => void
  isSidebarCollapsed?: boolean
  onToggleCollapse?: () => void
}

const VIEW_TITLES: Record<ActiveView, { title: string; subtitle: string }> = {
  dashboard: {
    title: "Dashboard Ejecutivo del SFPS (Visión Global 360°)",
    subtitle: "Proyecto ESPOCH - DI - 060 • Monitoreo macro y series de tiempo CAMEL"
  },
  benchmarking: {
    title: "Diagnóstico CAMEL & Benchmarking Institucional",
    subtitle: "Proyecto ESPOCH - DI - 060 • Comparador multi-cooperativa y semáforo normativo SEPS"
  },
  catalog: {
    title: "Catálogo de Indicadores SEPS V3.0",
    subtitle: "Proyecto ESPOCH - DI - 060 • Fichas técnicas, fórmulas y umbrales regulatorios"
  },
  entities: {
    title: "Directorio de Cooperativas de Ahorro y Crédito",
    subtitle: "Proyecto ESPOCH - DI - 060 • Padrón de entidades Segmentos 1 y 2 bajo supervisión"
  },
  admin_users: {
    title: "Gestión del Padrón de Usuarios Acreditados",
    subtitle: "Proyecto ESPOCH - DI - 060 • Administración de accesos, roles y contraseñas iniciales"
  },
  audit_logs: {
    title: "Bitácora de Auditoría Forense y Trazabilidad",
    subtitle: "Proyecto ESPOCH - DI - 060 • Control inmutable de accesos, descargas y eventos normativos"
  }
}

export const TopBar: React.FC<TopBarProps> = ({
  activeView,
  selectedDimension = "all",
  userRole,
  onToggleRole,
  onOpenMobileMenu,
  latestPeriod = "2025-12",
  dataAsOf,
  onExportReport,
  isSidebarCollapsed,
  onToggleCollapse
}) => {
  const isAccredited = userRole === "accredited"
  
  let currentTitle = VIEW_TITLES[activeView]?.title || "Sistema de Indicadores"
  let currentSubtitle = VIEW_TITLES[activeView]?.subtitle || "Proyecto ESPOCH - DI - 060"

  if (activeView === "dashboard" && selectedDimension !== "all") {
    const dim = CAMEL_DIMENSIONS.find((d) => d.id === selectedDimension)
    if (dim) {
      currentTitle = `Dashboard: ${dim.name}`
      currentSubtitle = `Dimensión CAMEL • ${dim.description}`
    }
  }

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 py-3 transition-all">
      <div className="flex items-center justify-between gap-4">
        {/* Lado izquierdo: Botón móvil + Botón colapso desktop + Título de la vista */}
        <div className="flex items-center gap-3">
          {/* Botón Móvil */}
          <button
            type="button"
            onClick={onOpenMobileMenu}
            className="p-2 -ml-2 rounded-lg text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Abrir menú"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight font-serif">
                {currentTitle}
              </h1>
              {activeView === "dashboard" && selectedDimension !== "all" && (
                <Badge variant="mint" className="hidden sm:inline-flex text-[10px] uppercase font-bold">
                  Dimensión
                </Badge>
              )}
              {activeView === "benchmarking" && (
                <Badge
                  variant={isAccredited ? "gold" : "slate"}
                  className="hidden sm:inline-flex text-[10px] uppercase font-bold"
                >
                  {isAccredited ? "Acreditado" : "Solo Consulta"}
                </Badge>
              )}
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              {currentSubtitle}
            </p>
          </div>
        </div>

        {/* Lado derecho: Estado de Credenciales y Periodo de Corte */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Pill de Corte */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200/80 text-xs font-medium text-slate-700">
            <Calendar className="h-3.5 w-3.5 text-emerald-700" />
            <span>Corte:</span>
            <span className="font-semibold text-slate-900">{latestPeriod}</span>
          </div>

          {/* Estado de Acceso Institucional */}
          {isAccredited ? (
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200/80 text-xs font-semibold text-emerald-900">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span>Acreditado</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggleRole}
                className="h-8 px-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                title="Cerrar sesión institucional"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={onToggleRole}
              className="flex items-center gap-2 text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 border-slate-200"
            >
              <LogIn className="h-3.5 w-3.5 text-emerald-700" />
              <span>Acceso Institucional</span>
            </Button>
          )}

          {/* Botón de Exportar si aplica */}
          {onExportReport && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportReport}
              className="gap-1.5 text-xs hidden sm:inline-flex"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Exportar</span>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
