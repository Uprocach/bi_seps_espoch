import React, { useState } from "react"
import { ShieldCheck, Lock, User, AlertCircle, Loader2, X, Sparkles } from "lucide-react"
import { useAuthStore } from "@/store/useAuthStore"
import type { Role } from "@/types/camel"

export const LoginModal: React.FC = () => {
  const { isLoginModalOpen, closeLoginModal, login, isLoading, error, clearError } = useAuthStore()
  
  const [username, setUsername] = useState("investigador.espoch")
  const [password, setPassword] = useState("EspochPro2026#")
  const [role, setRole] = useState<Role>("investigador")

  if (!isLoginModalOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    await login(username, password, role)
  }

  const handleQuickPreset = (presetRole: Role) => {
    setRole(presetRole)
    if (presetRole === "investigador") {
      setUsername("investigador.espoch")
      setPassword("EspochPro2026#")
    } else if (presetRole === "auditor") {
      setUsername("auditor.espoch")
      setPassword("EspochAuditor2026#")
    } else {
      setUsername("admin.espoch")
      setPassword("EspochAdmin2026#")
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-md p-6 bg-white border border-slate-200 rounded-2xl shadow-xl">
        {/* Botón cerrar */}
        <button
          onClick={closeLoginModal}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
          aria-label="Cerrar modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Encabezado */}
        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-100">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 font-serif flex items-center gap-2">
              Acreditación Institucional
              <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-700 text-white rounded-full">
                Capa Pro
              </span>
            </h3>
            <p className="text-xs text-slate-500">
              ESPOCH – DI – 060 | Supervisión SFPS
            </p>
          </div>
        </div>

        {/* Selector de Rol Institucional */}
        <div className="mb-4">
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Perfil de Acceso Institucional
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(["investigador", "auditor", "administrador"] as Role[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => handleQuickPreset(r)}
                className={`py-2 px-2 text-xs font-medium rounded-lg border transition-all text-center capitalize ${
                  role === r
                    ? "bg-emerald-50 border-emerald-600 text-emerald-800 font-bold shadow-xs"
                    : "border-slate-200 text-slate-600 hover:border-slate-300"
                }`}
              >
                {r === "administrador" ? "Admin" : r}
              </button>
            ))}
          </div>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Usuario Institucional
            </label>
            <div className="relative">
              <User className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="ej. investigador.espoch"
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:ring-1 focus:ring-emerald-600 focus:border-emerald-600 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Contraseña
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg text-slate-900 focus:ring-1 focus:ring-emerald-600 focus:border-emerald-600 focus:outline-none"
              />
            </div>
          </div>

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-xs text-rose-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900 text-white font-medium text-sm rounded-lg shadow-xs transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Autenticando...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Ingresar a la Capa Pro</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Nota de Seguridad y Soporte Institucional */}
        <div className="mt-4 pt-3 border-t border-slate-100 text-center space-y-2">
          <p className="text-[11px] text-slate-500 leading-relaxed">
            ¿Olvidaste tu contraseña?{" "}
            <span className="text-slate-700 font-medium dark:text-slate-300">
              Contacta a la administración del proyecto (<code>admin.espoch@espoch.edu.ec</code>) para emitir una clave temporal de desbloqueo.
            </span>
          </p>
          <div className="text-[10px] text-slate-400">
            Sesión protegida por HttpOnly Cookies criptográficas y cifrado institucional ESPOCH.
          </div>
        </div>
      </div>
    </div>
  )
}
