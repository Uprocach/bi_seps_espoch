import React, { useState, useEffect } from "react"
import {
  ShieldCheck,
  Search,
  RefreshCw,
  Loader2,
  Calendar,
  User,
  Activity,
  FileCode,
  Globe,
  ChevronLeft,
  ChevronRight,
  Filter,
  Eye,
  X
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { fetchAuditLogs, type AuditLogItem } from "@/services/apiClient"

export const AuditLogsView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filtros
  const [userInput, setUserInput] = useState("")
  const [actionInput, setActionInput] = useState("all")
  const [startDate, setStartDate] = useState("")
  const [endDate, setEndDate] = useState("")

  // Paginación
  const [page, setPage] = useState(1)
  const limit = 20

  // Modal de detalles
  const [selectedDetails, setSelectedDetails] = useState<{
    id: number
    action: string
    user: string
    timestamp: string
    details: Record<string, unknown>
  } | null>(null)

  const loadLogs = async (currentPage = page) => {
    try {
      setLoading(true)
      setError(null)
      const offset = (currentPage - 1) * limit
      const res = await fetchAuditLogs({
        limit,
        offset,
        user_sub: userInput.trim() || undefined,
        action: actionInput !== "all" ? actionInput : undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined
      })
      setLogs(res.logs)
      setTotal(res.total)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Error al consultar la bitácora de auditoría.")
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs(page)
  }, [page, actionInput])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadLogs(1)
  }

  const handleResetFilters = () => {
    setUserInput("")
    setActionInput("all")
    setStartDate("")
    setEndDate("")
    setPage(1)
  }

  const totalPages = Math.ceil(total / limit) || 1

  const getActionBadgeColor = (action: string) => {
    if (action.startsWith("auth:")) {
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800"
    }
    if (action.startsWith("admin:")) {
      return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800"
    }
    if (action.startsWith("export:")) {
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800"
    }
    return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800"
  }

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "administrador":
        return <Badge className="bg-purple-100 text-purple-800 border-purple-200 text-[11px]">Administrador</Badge>
      case "auditor":
        return <Badge className="bg-amber-100 text-amber-800 border-amber-200 text-[11px]">Auditor SFPS</Badge>
      default:
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200 text-[11px]">Investigador</Badge>
    }
  }

  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString("es-EC", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Bitácora de Auditoría Forense
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Registro cronológico inmutable de accesos, descargas masivas y gobernanza de la plataforma (AUD-13 / AUD-14).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="px-3 py-1 font-mono text-xs">
            Total Eventos: {total.toLocaleString()}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadLogs(page)}
            disabled={loading}
            className="flex items-center gap-1.5"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Barra de Filtros */}
      <form onSubmit={handleSearchSubmit} className="bg-slate-50 dark:bg-slate-900/60 p-4 rounded-xl border border-slate-200 dark:border-slate-800 grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Filtro Usuario */}
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1.5">
            Usuario
          </label>
          <div className="relative">
            <User className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por usuario..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Filtro Acción */}
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1.5">
            Acción / Categoría
          </label>
          <div className="relative">
            <Activity className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
            <select
              value={actionInput}
              onChange={(e) => {
                setActionInput(e.target.value)
                setPage(1)
              }}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">Todas las acciones</option>
              <option value="auth:login">auth:login (Inicio de sesión)</option>
              <option value="auth:logout">auth:logout (Cierre de sesión)</option>
              <option value="pro:benchmarking">pro:benchmarking (Análisis comparativo)</option>
              <option value="export:csv">export:csv (Descarga microdatos)</option>
              <option value="export:excel">export:excel (Reporte ejecutivo)</option>
              <option value="admin:create_user">admin:create_user (Alta de usuario)</option>
              <option value="admin:reset_password">admin:reset_password (Restablecimiento)</option>
              <option value="admin:toggle_active">admin:toggle_active (Estado cuenta)</option>
              <option value="admin:bulk_import_users">admin:bulk_import_users (Carga masiva)</option>
            </select>
          </div>
        </div>

        {/* Rango de Fechas */}
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1.5">
            Desde
          </label>
          <div className="relative">
            <Calendar className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1.5">
            Hasta
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Calendar className="h-4 w-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <Button type="submit" size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
              <Search className="h-3.5 w-3.5" />
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={handleResetFilters} title="Limpiar filtros">
              <Filter className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </form>

      {/* Error alert */}
      {error && (
        <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs">
          {error}
        </div>
      )}

      {/* Tabla de Eventos */}
      <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 font-semibold">
              <tr>
                <th className="px-4 py-3">ID</th>
                <th className="px-4 py-3">Fecha y Hora</th>
                <th className="px-4 py-3">Usuario</th>
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3">Acción</th>
                <th className="px-4 py-3">Recurso</th>
                <th className="px-4 py-3">Origen</th>
                <th className="px-4 py-3 text-right">Detalles</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400">
                    <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2 text-blue-600" />
                    Cargando eventos de auditoría...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-slate-400">
                    No se encontraron registros de auditoría que coincidan con los criterios.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-4 py-3 font-semibold text-slate-500">#{log.id}</td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-300 font-sans whitespace-nowrap">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">
                      {log.user_sub}
                    </td>
                    <td className="px-4 py-3 font-sans">
                      {getRoleBadge(log.user_role)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded border text-[11px] font-semibold ${getActionBadgeColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600 dark:text-slate-400 text-[11px] max-w-[200px] truncate" title={log.resource}>
                      {log.resource}
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-[11px]">
                      {log.ip_address || "127.0.0.1"}
                    </td>
                    <td className="px-4 py-3 text-right font-sans">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedDetails({
                          id: log.id,
                          action: log.action,
                          user: log.user_sub,
                          timestamp: log.timestamp,
                          details: log.details || {}
                        })}
                        className="h-7 px-2 text-xs text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Ver
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        <div className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400 font-sans">
          <div>
            Mostrando página <span className="font-semibold text-slate-800 dark:text-slate-200">{page}</span> de{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">{totalPages}</span> ({total} registros)
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              disabled={page <= 1 || loading}
              className="h-8 px-2.5 text-xs"
            >
              <ChevronLeft className="h-3.5 w-3.5 mr-1" />
              Anterior
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
              disabled={page >= totalPages || loading}
              className="h-8 px-2.5 text-xs"
            >
              Siguiente
              <ChevronRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </div>
        </div>
      </div>

      {/* Modal Inspector de Detalles */}
      {selectedDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <FileCode className="h-5 w-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                  Detalles del Evento #{selectedDetails.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedDetails(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-500">Acción:</span>{" "}
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  {selectedDetails.action}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Usuario:</span>{" "}
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  {selectedDetails.user}
                </span>
              </div>
              <div className="col-span-2">
                <span className="text-slate-500">Marca temporal UTC:</span>{" "}
                <span className="font-mono text-slate-800 dark:text-slate-200">
                  {selectedDetails.timestamp}
                </span>
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 block mb-1.5">
                Payload JSON Almacenado:
              </span>
              <pre className="bg-slate-950 text-emerald-400 p-3 rounded-lg text-[11px] font-mono overflow-x-auto max-h-60 border border-slate-800">
                {JSON.stringify(selectedDetails.details, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedDetails(null)}
                className="text-xs"
              >
                Cerrar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
