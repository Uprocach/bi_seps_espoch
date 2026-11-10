import { create } from "zustand"
import type { UserProfile, Role } from "@/types/camel"

interface AuthState {
  user: UserProfile | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  isLoginModalOpen: boolean

  // Actions
  checkAuth: () => Promise<void>
  login: (username: string, password: string, role?: Role) => Promise<boolean>
  logout: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<boolean>
  openLoginModal: () => void
  closeLoginModal: () => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  isLoginModalOpen: false,

  checkAuth: async () => {
    try {
      set({ isLoading: true, error: null })
      const res = await fetch("/api/v1/auth/me", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        credentials: "include"
      })

      if (res.ok) {
        const userData: UserProfile = await res.json()
        set({ user: userData, isAuthenticated: true, isLoading: false })
      } else {
        set({ user: null, isAuthenticated: false, isLoading: false })
      }
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  login: async (username: string, password: string, role: Role = "investigador") => {
    try {
      set({ isLoading: true, error: null })
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password, role })
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        const msg = errorData.detail || "Credenciales institucionales incorrectas."
        set({ error: msg, isLoading: false })
        return false
      }

      const userData: UserProfile = await res.json()
      set({
        user: userData,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isLoginModalOpen: false
      })
      return true
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error de conexión al autenticar."
      set({ error: msg, isLoading: false })
      return false
    }
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    try {
      set({ isLoading: true, error: null })
      const res = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        const msg = errorData.detail || "No se pudo actualizar la contraseña."
        set({ error: msg, isLoading: false })
        return false
      }

      const updatedUser: UserProfile = await res.json()
      set({ user: updatedUser, isLoading: false, error: null })
      return true
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error de red al cambiar contraseña."
      set({ error: msg, isLoading: false })
      return false
    }
  },

  logout: async () => {
    try {
      set({ isLoading: true })
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "include"
      })
    } finally {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null
      })
    }
  },

  openLoginModal: () => set({ isLoginModalOpen: true, error: null }),
  closeLoginModal: () => set({ isLoginModalOpen: false, error: null }),
  clearError: () => set({ error: null })
}))
