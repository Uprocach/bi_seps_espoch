import React, { useState } from "react"
import {
  LayoutDashboard,
  Scale,
  BookOpen,
  Building2,
  ShieldCheck,
  Users,
  Database,
  Lock,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
  GraduationCap,
  ShieldAlert,
  TrendingUp,
  Building,
  Droplets,
  Settings,
  ChevronDown,
  ChevronRight,
  Layers,
  LogIn,
  LogOut
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  CAMEL_DIMENSIONS,
  type IndicatorCategory
} from "@/data/extendedCatalog"

export type ActiveView = "dashboard" | "benchmarking" | "catalog" | "entities" | "admin_users"
export type UserRole = "public" | "accredited"

interface SidebarProps {
  activeView: ActiveView
  onSelectView: (view: ActiveView) => void
  selectedDimension: "all" | IndicatorCategory
  onSelectDimension: (dim: "all" | IndicatorCategory) => void
  userRole: UserRole
  onToggleRole: () => void
  latestPeriod?: string
  totalEntities?: number
  isMobileOpen?: boolean
  onCloseMobile?: () => void
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  systemRole?: string
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onSelectView,
  selectedDimension,
  onSelectDimension,
  userRole,
  onToggleRole,
  latestPeriod = "2025-12",
  totalEntities = 39,
  isMobileOpen = false,
  onCloseMobile,
  isCollapsed = false,
  onToggleCollapse,
  systemRole
}) => {
  const isAccredited = userRole === "accredited"
  const [isDimensionsOpen, setIsDimensionsOpen] = useState(true)

  const getDimensionIcon = (id: IndicatorCategory) => {
    switch (id) {
      case "calidad_de_activos":
        return ShieldAlert
      case "rentabilidad":
        return TrendingUp
      case "capital":
        return Building
      case "liquidez":
        return Droplets
      case "manejo_administrativo":
        return Settings
      default:
        return Layers
    }
  }

  const handleGlobalClick = () => {
    onSelectView("dashboard")
    onSelectDimension("all")
    if (onCloseMobile) onCloseMobile()
  }

  const handleDimensionClick = (dimId: IndicatorCategory) => {
    onSelectView("dashboard")
    onSelectDimension(dimId)
    if (onCloseMobile) onCloseMobile()
  }

  return (
    <>
      {/* Overlay para móviles */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 bg-white border-r border-slate-200/90 flex flex-col transition-all duration-300 ease-in-out lg:translate-x-0 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        } ${isCollapsed ? "w-20" : "w-72"}`}
      >
        {/* Cabecera / Marca ESPOCH - DI - 060 */}
        <div
          className={`p-4 border-b border-slate-100 bg-gradient-to-b from-emerald-50/50 to-transparent flex items-center ${
            isCollapsed ? "justify-center" : "justify-between"
          }`}
        >
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="h-10 w-10 shrink-0 rounded-xl bg-gradient-to-br from-emerald-700 to-teal-800 flex items-center justify-center text-white shadow-md shadow-emerald-900/15 ring-2 ring-emerald-600/20"
              title="ESPOCH - DI - 060"
            >
              <GraduationCap className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-slate-900 text-sm tracking-tight font-serif truncate">
                    ESPOCH
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded shrink-0">
                    DI - 060
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 font-medium truncate">
                  Investigación SFPS • SEPS
                </p>
              </div>
            )}
          </div>

          {/* Botón de Colapsar en Desktop */}
          {!isCollapsed && onToggleCollapse && (
            <button
              type="button"
              onClick={onToggleCollapse}
              className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              title="Colapsar menú lateral"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Botón de expandir si está colapsado */}
        {isCollapsed && onToggleCollapse && (
          <div className="hidden lg:flex justify-center py-2 border-b border-slate-100">
            <button
              type="button"
              onClick={onToggleCollapse}
              className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-700 hover:bg-emerald-50 transition-colors"
              title="Expandir menú lateral"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Navegación Principal */}
        <nav className="flex-1 p-2.5 space-y-1 overflow-y-auto">
          {/* 1. Visión Global 360° */}
          <button
            type="button"
            onClick={handleGlobalClick}
            title={isCollapsed ? "Visión Global 360° (Dashboard General)" : undefined}
            className={`w-full text-left rounded-xl text-xs transition-all flex items-center group ${
              isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
            } ${
              activeView === "dashboard" && selectedDimension === "all"
                ? "bg-emerald-50/90 text-emerald-950 font-semibold border border-emerald-200/90 shadow-2xs"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`p-1.5 rounded-lg transition-colors ${
                  activeView === "dashboard" && selectedDimension === "all"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                }`}
              >
                <LayoutDashboard className="h-4 w-4" />
              </div>
              {!isCollapsed && (
                <div className="min-w-0">
                  <div className="truncate font-semibold">Visión Global 360°</div>
                  <p className="text-[10px] text-slate-400 font-normal truncate">
                    Resumen macro CAMEL
                  </p>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <Badge variant="mint" className="text-[10px] px-1.5 py-0">
                Público
              </Badge>
            )}
          </button>

          {/* 2. Sección: Dashboards Especializados por Dimensión CAMEL */}
          <div className="pt-2">
            {!isCollapsed ? (
              <div className="flex items-center justify-between px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                <span>Dashboards CAMEL</span>
                <button
                  type="button"
                  onClick={() => setIsDimensionsOpen((prev) => !prev)}
                  className="hover:text-slate-600 p-0.5 rounded"
                  title={isDimensionsOpen ? "Ocultar dimensiones" : "Mostrar dimensiones"}
                >
                  {isDimensionsOpen ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </button>
              </div>
            ) : (
              <div className="border-t border-slate-100 my-1 pt-1" />
            )}

            {(isDimensionsOpen || isCollapsed) && (
              <div className="space-y-0.5 mt-0.5">
                {CAMEL_DIMENSIONS.map((dim) => {
                  const Icon = getDimensionIcon(dim.id)
                  const isActive =
                    activeView === "dashboard" && selectedDimension === dim.id

                  return (
                    <button
                      key={dim.id}
                      type="button"
                      onClick={() => handleDimensionClick(dim.id)}
                      title={isCollapsed ? `${dim.name} (${dim.badge})` : undefined}
                      className={`w-full text-left rounded-lg text-xs transition-all flex items-center group ${
                        isCollapsed
                          ? "justify-center p-2"
                          : "justify-between px-2.5 py-2 pl-3"
                      } ${
                        isActive
                          ? "bg-emerald-100/70 text-emerald-950 font-bold border border-emerald-300/80 shadow-2xs"
                          : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div
                          className={`p-1 rounded-md transition-colors ${
                            isActive
                              ? "bg-emerald-700 text-white"
                              : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        {!isCollapsed && (
                          <div className="min-w-0">
                            <span className="truncate block text-xs">
                              {dim.shortName}
                            </span>
                          </div>
                        )}
                      </div>

                      {!isCollapsed && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          {dim.badge}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Separador */}
          <div className="border-t border-slate-100 my-2 pt-1" />

          {!isCollapsed && (
            <div className="px-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              Herramientas
            </div>
          )}

          {/* 3. Benchmarking Pro */}
          <button
            type="button"
            onClick={() => {
              onSelectView("benchmarking")
              if (onCloseMobile) onCloseMobile()
            }}
            title={isCollapsed ? "Benchmarking Pro (Comparador Multi-Entidad)" : undefined}
            className={`w-full text-left rounded-xl text-xs transition-all flex items-center group ${
              isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
            } ${
              activeView === "benchmarking"
                ? "bg-emerald-50/90 text-emerald-950 font-semibold border border-emerald-200/90 shadow-2xs"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`p-1.5 rounded-lg transition-colors ${
                  activeView === "benchmarking"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                }`}
              >
                <Scale className="h-4 w-4" />
              </div>
              {!isCollapsed && (
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-semibold">Benchmarking Pro</span>
                    {!isAccredited && (
                      <Lock className="h-3 w-3 text-amber-500 shrink-0" />
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 font-normal truncate">
                    Comparador & semáforo SEPS
                  </p>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <Badge
                variant={isAccredited ? "gold" : "slate"}
                className="text-[10px] px-1.5 py-0"
              >
                {isAccredited ? "Activo" : "Pro"}
              </Badge>
            )}
          </button>

          {/* 4. Catálogo SEPS V3.0 */}
          <button
            type="button"
            onClick={() => {
              onSelectView("catalog")
              if (onCloseMobile) onCloseMobile()
            }}
            title={isCollapsed ? "Catálogo de Indicadores SEPS V3.0" : undefined}
            className={`w-full text-left rounded-xl text-xs transition-all flex items-center group ${
              isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
            } ${
              activeView === "catalog"
                ? "bg-emerald-50/90 text-emerald-950 font-semibold border border-emerald-200/90 shadow-2xs"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`p-1.5 rounded-lg transition-colors ${
                  activeView === "catalog"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                }`}
              >
                <BookOpen className="h-4 w-4" />
              </div>
              {!isCollapsed && (
                <div className="min-w-0">
                  <span className="truncate font-semibold">Catálogo SEPS V3.0</span>
                  <p className="text-[10px] text-slate-400 font-normal truncate">
                    20+ fichas normativas
                  </p>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <Badge variant="mint" className="text-[10px] px-1.5 py-0">
                Norma
              </Badge>
            )}
          </button>

          {/* 5. Directorio de Cooperativas */}
          <button
            type="button"
            onClick={() => {
              onSelectView("entities")
              if (onCloseMobile) onCloseMobile()
            }}
            title={isCollapsed ? "Directorio de Cooperativas Segmentos 1 y 2" : undefined}
            className={`w-full text-left rounded-xl text-xs transition-all flex items-center group ${
              isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
            } ${
              activeView === "entities"
                ? "bg-emerald-50/90 text-emerald-950 font-semibold border border-emerald-200/90 shadow-2xs"
                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`p-1.5 rounded-lg transition-colors ${
                  activeView === "entities"
                    ? "bg-emerald-600 text-white"
                    : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                }`}
              >
                <Building2 className="h-4 w-4" />
              </div>
              {!isCollapsed && (
                <div className="min-w-0">
                  <span className="truncate font-semibold">Directorio</span>
                  <p className="text-[10px] text-slate-400 font-normal truncate">
                    Segmentos 1 y 2
                  </p>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <Badge variant="slate" className="text-[10px] px-1.5 py-0">
                {totalEntities}
              </Badge>
            )}
          </button>

          {/* 6. Panel de Administración de Usuarios (Solo Administrador) */}
          {systemRole === "administrador" && (
            <button
              type="button"
              onClick={() => {
                onSelectView("admin_users")
                if (onCloseMobile) onCloseMobile()
              }}
              title={isCollapsed ? "Gestión de Usuarios Acreditados" : undefined}
              className={`w-full text-left rounded-xl text-xs transition-all flex items-center group ${
                isCollapsed ? "justify-center p-2.5" : "justify-between px-3 py-2.5"
              } ${
                activeView === "admin_users"
                  ? "bg-purple-50/90 text-purple-950 font-semibold border border-purple-200/90 shadow-2xs"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div
                  className={`p-1.5 rounded-lg transition-colors ${
                    activeView === "admin_users"
                      ? "bg-purple-600 text-white"
                      : "bg-slate-100 text-slate-500 group-hover:bg-slate-200 group-hover:text-slate-800"
                  }`}
                >
                  <Users className="h-4 w-4" />
                </div>
                {!isCollapsed && (
                  <div className="min-w-0">
                    <span className="truncate font-semibold">Usuarios</span>
                    <p className="text-[10px] text-slate-400 font-normal truncate">
                      Padrón acreditado
                    </p>
                  </div>
                )}
              </div>
              {!isCollapsed && (
                <Badge variant="gold" className="text-[10px] px-1.5 py-0 bg-purple-100 text-purple-800 border-purple-200">
                  Admin
                </Badge>
              )}
            </button>
          )}
        </nav>

        {/* Footer del Sidebar: Botón simple y discreto para Iniciar / Cerrar Sesión */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/60">
          <Button
            variant={isAccredited ? "outline" : "ghost"}
            size="sm"
            onClick={onToggleRole}
            className={`w-full text-xs font-medium h-9 text-slate-700 hover:text-slate-900 hover:bg-white hover:border-slate-200 transition-all ${
              isCollapsed ? "justify-center px-0" : "justify-between px-3"
            }`}
            title={isCollapsed ? (isAccredited ? "Cerrar sesión" : "Iniciar sesión") : undefined}
          >
            <div className="flex items-center gap-2 min-w-0">
              {isAccredited ? (
                <LogOut className="h-4 w-4 text-slate-500 shrink-0" />
              ) : (
                <LogIn className="h-4 w-4 text-emerald-700 shrink-0" />
              )}
              {!isCollapsed && (
                <span className="truncate font-semibold">
                  {isAccredited ? "Cerrar Sesión" : "Iniciar Sesión"}
                </span>
              )}
            </div>
            {!isCollapsed && isAccredited && (
              <Badge variant="gold" className="text-[9px] px-1.5 py-0 h-4">
                Pro
              </Badge>
            )}
          </Button>
        </div>
      </aside>
    </>
  )
}
