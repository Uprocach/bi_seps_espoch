import React, { useEffect } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Sidebar, type UserRole } from "@/components/Sidebar"
import { TopBar } from "@/components/TopBar"
import { DashboardView } from "@/components/views/DashboardView"
import { BenchmarkingView } from "@/components/views/BenchmarkingView"
import { CatalogView } from "@/components/views/CatalogView"
import { EntitiesView } from "@/components/views/EntitiesView"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { LoginModal } from "@/components/auth/LoginModal"
import { ChangePasswordModal } from "@/components/auth/ChangePasswordModal"
import { AdminUsersView } from "@/components/views/AdminUsersView"
import { AuditLogsView } from "@/components/views/AuditLogsView"
import { useAuthStore } from "@/store/useAuthStore"
import { useDashboardStore } from "@/store/useDashboardStore"
import { useMetadataFiltersQuery, useEntitiesQuery } from "@/hooks/useIndicatorsQueries"

// Singleton de TanStack Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000
    }
  }
})

const AppContent: React.FC = () => {
  const { user, isAuthenticated, checkAuth, openLoginModal, logout } = useAuthStore()
  const store = useDashboardStore()

  // Queries reactivas globales para cabeceras y sidebar
  const { data: metadata } = useMetadataFiltersQuery()
  const { data: entitiesData } = useEntitiesQuery({ pageSize: 1 })

  const userRole: UserRole = isAuthenticated ? "accredited" : "public"

  // 1. Validar sesión HttpOnly al montar
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  // 2. Garantizar que usuarios sin acreditar no queden en vistas restringidas
  useEffect(() => {
    if (
      !isAuthenticated &&
      (store.activeView === "benchmarking" ||
        store.activeView === "admin_users" ||
        store.activeView === "audit_logs")
    ) {
      store.setActiveView("dashboard")
    }
  }, [isAuthenticated, store.activeView, store])

  const handleToggleRole = () => {
    if (isAuthenticated) {
      logout()
    } else {
      openLoginModal()
    }
  }

  return (
    <div className="min-h-screen bg-slate-50/70 flex font-sans text-slate-800 antialiased selection:bg-emerald-200">
      <LoginModal />
      <ChangePasswordModal />

      {/* Menú Lateral Desacoplado */}
      <Sidebar
        activeView={store.activeView}
        onSelectView={store.setActiveView}
        selectedDimension={store.selectedDimension}
        onSelectDimension={store.setSelectedDimension}
        userRole={userRole}
        onToggleRole={handleToggleRole}
        latestPeriod={metadata?.periods.latest}
        totalEntities={entitiesData?.pagination.total_items || 39}
        isMobileOpen={store.isMobileMenuOpen}
        onCloseMobile={() => store.setIsMobileMenuOpen(false)}
        isCollapsed={store.isSidebarCollapsed}
        onToggleCollapse={() => store.setIsSidebarCollapsed(!store.isSidebarCollapsed)}
        systemRole={user?.role}
      />

      {/* Área Principal de Contenido */}
      <div
        className={`flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden transition-all duration-300 ease-in-out ${
          store.isSidebarCollapsed ? "lg:pl-20" : "lg:pl-72"
        }`}
      >
        <TopBar
          activeView={store.activeView}
          selectedDimension={store.selectedDimension}
          userRole={userRole}
          onToggleRole={handleToggleRole}
          onOpenMobileMenu={() => store.setIsMobileMenuOpen(true)}
          latestPeriod={metadata?.periods.latest}
          dataAsOf={metadata?.data_as_of}
          isSidebarCollapsed={store.isSidebarCollapsed}
          onToggleCollapse={() => store.setIsSidebarCollapsed(!store.isSidebarCollapsed)}
        />

        <main className="flex-1 p-4 lg:p-6 max-w-7xl w-full mx-auto space-y-6">
          {store.activeView === "dashboard" && <DashboardView />}

          {isAuthenticated && store.activeView === "benchmarking" && (
            <ProtectedRoute
              requiredRoles={["investigador", "auditor", "administrador"]}
              fallbackTitle="Diagnóstico CAMEL & Supervisión Institucional"
              fallbackDescription="El comparador analítico de cooperativas supervisadas con semáforo regulatorio SEPS v3.0 está reservado para perfiles institucionales acreditados."
            >
              <BenchmarkingView />
            </ProtectedRoute>
          )}

          {store.activeView === "catalog" && <CatalogView />}

          {store.activeView === "entities" && <EntitiesView />}

          {store.activeView === "admin_users" && (
            <ProtectedRoute
              requiredRoles={["administrador"]}
              fallbackTitle="Panel de Administración Exclusivo"
              fallbackDescription="La gestión del padrón de usuarios institucionales está restringida exclusivamente a usuarios con rol de Administrador."
            >
              <AdminUsersView />
            </ProtectedRoute>
          )}

          {store.activeView === "audit_logs" && (
            <ProtectedRoute
              requiredRoles={["auditor", "administrador"]}
              fallbackTitle="Módulo de Auditoría Forense"
              fallbackDescription="La consulta y trazabilidad de eventos del sistema está reservada para usuarios con rol de Auditor o Administrador."
            >
              <AuditLogsView />
            </ProtectedRoute>
          )}
        </main>

        <footer className="border-t border-slate-200/80 bg-white py-5 px-6 lg:px-8 text-xs text-slate-500 mt-auto w-full">
          <div className="w-full flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-800">ESPOCH - DI - 060</span>
              <span>•</span>
              <span>Sistema de Indicadores SFPS</span>
              <span>•</span>
              <span>Motor Analítico DuckDB & Gobernanza RBAC</span>
            </div>
            <div className="font-mono text-[11px] text-slate-400">
              Dirección de Investigación ESPOCH • Fichas Metodológicas SEPS V3.0
            </div>
          </div>
        </footer>
      </div>
    </div>
  )
}

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}

export default App
