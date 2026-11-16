import { create } from "zustand"
import type { UserProfile, Role } from "@/types/camel"
import {
  fetchCurrentUser,
  loginWithCredentials,
  changeUserPassword,
  logoutSession
} from "@/services/httpClient"

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
      const userData = await fetchCurrentUser()
      set({ user: userData, isAuthenticated: true, isLoading: false })
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  login: async (username: string, password: string, role: Role = "investigador") => {
    try {
      set({ isLoading: true, error: null })
      const userData = await loginWithCredentials(username, password, role)
      set({
        user: userData,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        isLoginModalOpen: false
      })
      return true
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Credenciales institucionales incorrectas."
      set({ error: msg, isLoading: false })
      return false
    }
  },

  changePassword: async (currentPassword: string, newPassword: string) => {
    try {
      set({ isLoading: true, error: null })
      const updatedUser = await changeUserPassword(currentPassword, newPassword)
      set({ user: updatedUser, isLoading: false, error: null })
      return true
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "No se pudo actualizar la contraseña."
      set({ error: msg, isLoading: false })
      return false
    }
  },

  logout: async () => {
    try {
      set({ isLoading: true })
      await logoutSession()
    } catch {
      // Limpiar estado local incluso si la sesión ya expiró
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
