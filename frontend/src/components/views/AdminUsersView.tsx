import React, { useState, useEffect } from "react"
import {
  Users,
  UserPlus,
  Upload,
  Download,
  KeyRound,
  Shield,
  Search,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Loader2,
  FileSpreadsheet
} from "lucide-react"
import type { AdminUserListItem, Role } from "@/types/camel"
import { PipelineSyncCard } from "@/components/admin/PipelineSyncCard"


export const AdminUsersView: React.FC = () => {
  const [users, setUsers] = useState<AdminUserListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState<string>("all")
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  // Modales
  const [isNewUserModalOpen, setIsNewUserModalOpen] = useState(false)
  const [isBulkModalOpen, setIsBulkModalOpen] = useState(false)

  // Formulario Nuevo Usuario
  const [newUsername, setNewUsername] = useState("")
  const [newEmail, setNewEmail] = useState("")
  const [newFullName, setNewFullName] = useState("")
  const [newRole, setNewRole] = useState<Role>("investigador")
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Formulario Bulk Import
  const [bulkCsvText, setBulkCsvText] = useState("")
  const [bulkResult, setBulkResult] = useState<{ imported: number; errors: string[] } | null>(null)

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/v1/admin/users", {
        credentials: "include"
      })
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
      } else {
        setStatusMessage({ type: "error", text: "Error al cargar el listado de usuarios." })
      }
    } catch {
      setStatusMessage({ type: "error", text: "Error de conexión al cargar usuarios." })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setStatusMessage(null)

    try {
      const res = await fetch("/api/v1/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username: newUsername,
          email: newEmail,
          full_name: newFullName,
          role: newRole
        })
      })

      if (res.ok) {
        setStatusMessage({
          type: "success",
          text: `Usuario ${newUsername} creado exitosamente con contraseña temporal '${newUsername}'.`
        })
        setIsNewUserModalOpen(false)
        setNewUsername("")
        setNewEmail("")
        setNewFullName("")
        fetchUsers()
      } else {
        const err = await res.json().catch(() => ({}))
        setStatusMessage({ type: "error", text: err.detail || "No se pudo crear el usuario." })
      }
    } catch {
      setStatusMessage({ type: "error", text: "Error de red al registrar usuario." })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBulkImport = async () => {
    if (!bulkCsvText.trim()) return
    setIsSubmitting(true)
    setBulkResult(null)

    // Parsear líneas CSV simples (nombre, email, rol)
    const lines = bulkCsvText.trim().split("\n")
    const parsedUsers = []

    for (const rawLine of lines) {
      const line = rawLine.trim()
      if (!line || line.toLowerCase().startsWith("nombre") || line.toLowerCase().startsWith("full_name")) {
        continue
      }
      const parts = line.split(",").map((p) => p.trim())
      if (parts.length >= 2) {
        const fullName = parts[0]
        const email = parts[1]
        const role = (parts[2] || "investigador").toLowerCase() as Role
        const username = email.split("@")[0]
        parsedUsers.push({
          full_name: fullName,
          email,
          username,
          role
        })
      }
    }

    if (parsedUsers.length === 0) {
      setStatusMessage({ type: "error", text: "El formato CSV no contiene registros válidos." })
      setIsSubmitting(false)
      return
    }

    try {
      const res = await fetch("/api/v1/admin/users/bulk-import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ users: parsedUsers })
      })

      if (res.ok) {
        const data = await res.json()
        setBulkResult({ imported: data.imported_count, errors: data.errors || [] })
        setStatusMessage({
          type: "success",
          text: `Se importaron ${data.imported_count} usuarios exitosamente. Contraseña temporal asignada: nombre.apellido`
        })
        fetchUsers()
      } else {
        setStatusMessage({ type: "error", text: "Error al procesar la importación masiva." })
      }
    } catch {
      setStatusMessage({ type: "error", text: "Error de conexión en carga masiva." })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleResetPassword = async (userId: number, username: string) => {
    if (!confirm(`¿Restablecer la contraseña de ${username} a su clave temporal '${username}'?`)) {
      return
    }

    try {
      const res = await fetch(`/api/v1/admin/users/${userId}/reset-password`, {
        method: "POST",
        credentials: "include"
      })
      if (res.ok) {
        setStatusMessage({
          type: "success",
          text: `Contraseña de ${username} restablecida a '${username}'. Deberá cambiarla al entrar.`
        })
        fetchUsers()
      } else {
        setStatusMessage({ type: "error", text: "No se pudo restablecer la contraseña." })
      }
    } catch {
      setStatusMessage({ type: "error", text: "Error de red al restablecer contraseña." })
    }
  }

  const handleToggleActive = async (userId: number) => {
    try {
      const res = await fetch(`/api/v1/admin/users/${userId}/toggle-active`, {
        method: "PATCH",
        credentials: "include"
      })
      if (res.ok) {
        fetchUsers()
      } else {
        const err = await res.json().catch(() => ({}))
        setStatusMessage({ type: "error", text: err.detail || "No se pudo modificar el estado." })
      }
    } catch {
      setStatusMessage({ type: "error", text: "Error de conexión al alternar estado del usuario." })
    }
  }

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.full_name.toLowerCase().includes(search.toLowerCase()) ||
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())

    const matchesRole = roleFilter === "all" || u.role === roleFilter
    return matchesSearch && matchesRole
  })

  const totalActive = users.filter((u) => u.is_active).length
  const totalPendingChange = users.filter((u) => u.must_change_password).length

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Encabezado y Métricas */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            Gestión de Usuarios Acreditados
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Administración del padrón institucional de investigadores, auditores y directivos (Proyecto ESPOCH-DI-060).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href="/api/v1/admin/users/template-csv"
            download
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <Download className="h-3.5 w-3.5 text-slate-500" />
            Descargar Plantilla CSV
          </a>
          <button
            onClick={() => {
              setBulkResult(null)
              setIsBulkModalOpen(true)
            }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-600 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 dark:border-emerald-500 dark:bg-emerald-950/40 dark:text-emerald-300"
          >
            <Upload className="h-3.5 w-3.5" />
            Importar Lista (CSV)
          </button>
          <button
            onClick={() => setIsNewUserModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-500"
          >
            <UserPlus className="h-3.5 w-3.5" />
            Nuevo Usuario
          </button>
        </div>
      </div>

      {/* Alerta de Estado */}
      {statusMessage && (
        <div
          className={`flex items-center justify-between rounded-lg p-3 text-xs shadow-sm ${
            statusMessage.type === "success"
              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800"
              : "bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === "success" ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="text-slate-400 hover:text-slate-600">
            ×
          </button>
        </div>
      )}

      {/* Sincronización Web SEPS y Pipeline Zero-Downtime */}
      <PipelineSyncCard />

      {/* Tarjetas de Resumen */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Padrón Total</span>
          <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{users.length}</p>
          <span className="text-[10px] text-slate-400">Cuentas registradas en el sistema</span>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Usuarios Activos</span>
          <p className="mt-1 text-2xl font-bold text-emerald-600 dark:text-emerald-400">{totalActive}</p>
          <span className="text-[10px] text-slate-400">Habilitados para consultar microdatos</span>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Pendientes Cambio de Clave</span>
          <p className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{totalPendingChange}</p>
          <span className="text-[10px] text-slate-400">Con contraseña temporal de primer acceso</span>
        </div>
      </div>

      {/* Barra de Filtros y Búsqueda */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, correo (ej. @espoch.edu.ec) o usuario..."
            className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 py-1.5 text-xs text-slate-900 focus:border-emerald-500 focus:bg-white focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-white"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 focus:border-emerald-500 focus:outline-none dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          >
            <option value="all">Todos los Roles</option>
            <option value="investigador">Investigadores</option>
            <option value="auditor">Auditores</option>
            <option value="administrador">Administradores</option>
          </select>
          <button
            onClick={() => fetchUsers()}
            title="Recargar listado"
            className="rounded-lg border border-slate-200 bg-slate-50 p-1.5 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Tabla de Usuarios */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
            <thead className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-800/60 dark:text-slate-200">
              <tr>
                <th className="px-4 py-3">Nombre Completo</th>
                <th className="px-4 py-3">Usuario Institucional</th>
                <th className="px-4 py-3">Correo Institucional</th>
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3 text-center">Estado</th>
                <th className="px-4 py-3 text-center">Clave</th>
                <th className="px-4 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading && users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin text-emerald-600" />
                    <span className="mt-2 block text-xs">Cargando usuarios...</span>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No se encontraron usuarios con los criterios de búsqueda.
                  </td>
                </tr>
              ) : (
                filteredUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                      {u.full_name}
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                      {u.username}
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      {u.email}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-medium capitalize ${
                          u.role === "administrador"
                            ? "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300"
                            : u.role === "auditor"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300"
                            : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
                        }`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                          u.is_active
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-slate-400 dark:text-slate-500 line-through"
                        }`}
                      >
                        {u.is_active ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                        {u.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {u.must_change_password ? (
                        <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200/60 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/40">
                          Temporal
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400">Personal</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleResetPassword(u.id, u.username)}
                          title="Restablecer a contraseña temporal (nombre.apellido)"
                          className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-amber-600 dark:hover:bg-slate-800 dark:hover:text-amber-400"
                        >
                          <KeyRound className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleToggleActive(u.id)}
                          title={u.is_active ? "Desactivar acceso" : "Reactivar acceso"}
                          className={`rounded px-2 py-0.5 text-[10px] font-medium border ${
                            u.is_active
                              ? "border-slate-200 text-slate-600 hover:bg-rose-50 hover:text-rose-600 dark:border-slate-700 dark:text-slate-300"
                              : "border-emerald-300 text-emerald-600 hover:bg-emerald-50 dark:border-emerald-800 dark:text-emerald-400"
                          }`}
                        >
                          {u.is_active ? "Desactivar" : "Activar"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Nuevo Usuario */}
      {isNewUserModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-emerald-600" />
              Registrar Usuario Institucional
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              La contraseña inicial temporal será idéntica al nombre de usuario (ej. <code>nombre.apellido</code>).
            </p>

            <form onSubmit={handleCreateUser} className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Nombre Completo
                </label>
                <input
                  type="text"
                  required
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="Ej: Ing. Marco Vinicio"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Correo Institucional (@espoch.edu.ec)
                </label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => {
                    const val = e.target.value
                    setNewEmail(val)
                    if (val.includes("@") && !newUsername) {
                      setNewUsername(val.split("@")[0].toLowerCase())
                    }
                  }}
                  placeholder="marco.vinicio@espoch.edu.ec"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Usuario Institucional (Nombre de Acceso)
                </label>
                <input
                  type="text"
                  required
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value.toLowerCase())}
                  placeholder="marco.vinicio"
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-mono text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                  Rol Asignado
                </label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as Role)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
                >
                  <option value="investigador">Investigador (Lectura Pro + CSV)</option>
                  <option value="auditor">Auditor (Descarga Excel + Logs)</option>
                  <option value="administrador">Administrador (Control Total)</option>
                </select>
              </div>

              <div className="mt-5 flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewUserModalOpen(false)}
                  className="rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {isSubmitting ? "Registrando..." : "Crear Usuario"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Importación Masiva (CSV) */}
      {isBulkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl dark:bg-slate-900">
            <h3 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Upload className="h-5 w-5 text-emerald-600" />
              Carga Masiva de Usuarios (Padrón ~100)
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Pega aquí el contenido de tu archivo CSV con el formato: <code>nombre, correo, rol</code>.
              La primera contraseña de cada usuario será su identificador (ej. <code>nombre.apellido</code>).
            </p>

            <div className="mt-3">
              <textarea
                rows={8}
                value={bulkCsvText}
                onChange={(e) => setBulkCsvText(e.target.value)}
                placeholder={"Juan Perez, juan.perez@espoch.edu.ec, investigador\nMaria Lopez, maria.lopez@espoch.edu.ec, auditor\nCarlos Gomez, carlos.gomez@espoch.edu.ec, investigador"}
                className="w-full font-mono rounded-lg border border-slate-300 p-2.5 text-xs text-slate-900 focus:border-emerald-500 dark:border-slate-700 dark:bg-slate-800 dark:text-white"
              />
            </div>

            {bulkResult && (
              <div className="mt-3 rounded-lg bg-slate-50 p-2.5 text-xs dark:bg-slate-800">
                <p className="font-semibold text-emerald-600">
                  ✓ {bulkResult.imported} usuarios importados con éxito.
                </p>
                {bulkResult.errors.length > 0 && (
                  <ul className="mt-1.5 space-y-0.5 text-rose-600 text-[11px]">
                    {bulkResult.errors.map((err, i) => (
                      <li key={i}>• {err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div className="mt-5 flex items-center justify-between pt-2">
              <a
                href="/api/v1/admin/users/template-csv"
                download
                className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:underline"
              >
                <Download className="h-3 w-3" />
                Descargar formato ejemplo
              </a>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsBulkModalOpen(false)}
                  className="rounded-lg px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700"
                >
                  Cerrar
                </button>
                <button
                  type="button"
                  onClick={handleBulkImport}
                  disabled={isSubmitting || !bulkCsvText.trim()}
                  className="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                >
                  {isSubmitting ? "Importando..." : "Importar Padrón"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
