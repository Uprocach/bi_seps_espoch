import React from "react"
import { ShieldAlert, Lock, ArrowRight } from "lucide-react"
import { useAuthStore } from "@/store/useAuthStore"
import type { Role } from "@/types/camel"
import { Button } from "@/components/ui/button"

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRoles?: Role[]
  fallbackTitle?: string
  fallbackDescription?: string
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRoles = ["investigador", "auditor", "administrador"],
  fallbackTitle = "Herramienta de Supervisión y Benchmarking Restringida",
  fallbackDescription = "El motor analítico multi-entidad con semáforo normativo de alertas tempranas está reservado para Unidades de Riesgo, Auditores y el Equipo de Investigación ESPOCH."
}) => {
  const { isAuthenticated, user, openLoginModal } = useAuthStore()

  if (!isAuthenticated || !user) {
    return (
      <div className="flex flex-col items-center justify-center p-8 md:p-14 my-6 bg-white border border-slate-200/80 rounded-2xl max-w-2xl mx-auto text-center shadow-xs">
        <div className="p-3.5 bg-emerald-50 text-emerald-700 rounded-2xl mb-4 border border-emerald-100">
          <Lock className="w-7 h-7" />
        </div>
        <h3 className="text-xl font-bold text-slate-900 font-serif mb-2">
          {fallbackTitle}
        </h3>
        <p className="text-xs sm:text-sm text-slate-500 mb-6 max-w-md leading-relaxed">
          {fallbackDescription}
        </p>
        <Button
          onClick={openLoginModal}
          className="gap-2 bg-emerald-700 hover:bg-emerald-800 text-white font-medium text-xs px-5 py-2.5 rounded-xl shadow-xs"
        >
          <span>Acceder con Credenciales Institucionales</span>
          <ArrowRight className="w-4 h-4" />
        </Button>
      </div>
    )
  }

  // Verificar si el rol cumple los requerimientos
  const userRole = user.role
  const isAllowed = requiredRoles.includes(userRole)

  if (!isAllowed) {
    return (
      <div className="flex flex-col items-center justify-center p-8 md:p-12 my-6 bg-rose-50/50 border border-rose-200 rounded-2xl max-w-xl mx-auto text-center">
        <div className="p-3 bg-rose-100 text-rose-600 rounded-xl mb-3">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-base font-bold text-rose-900 mb-1">
          Permisos Insuficientes (HTTP 403)
        </h3>
        <p className="text-xs text-rose-700 mb-4 max-w-md">
          Tu rol actual (<span className="font-semibold">{userRole}</span>) no cuenta con autorización para este módulo.
          Roles admitidos: {requiredRoles.join(", ")}.
        </p>
      </div>
    )
  }

  return <>{children}</>
}
