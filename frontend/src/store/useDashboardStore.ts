/**
 * Store Global de Filtros y Navegación del Dashboard (ESPOCH-DI-060)
 * Elimina la maraña de 15 variables de estado y prop drilling en App.tsx.
 */

import { create } from "zustand"
import type { SegmentCode, AggregationLevel } from "@/services/httpClient"
import type { IndicatorCategory } from "@/data/extendedCatalog"

export type ActiveView =
  | "dashboard"
  | "entities"
  | "benchmarking"
  | "catalog"
  | "admin_users"
  | "audit_logs"

interface DashboardState {
  // Navegación
  activeView: ActiveView
  selectedDimension: "all" | IndicatorCategory
  isMobileMenuOpen: boolean
  isSidebarCollapsed: boolean

  // Filtros de series y dashboard
  selectedIndicator: string
  level: AggregationLevel
  selectedSegments: SegmentCode[]
  selectedProvince: string
  fromPeriod: string
  toPeriod: string
  selectedRucs: string[]

  // Filtros de directorio de entidades
  searchQuery: string
  entityPage: number

  // Acciones
  setActiveView: (view: ActiveView) => void
  setSelectedDimension: (dim: "all" | IndicatorCategory) => void
  setIsMobileMenuOpen: (open: boolean) => void
  setIsSidebarCollapsed: (collapsed: boolean) => void
  setSelectedIndicator: (indicator: string) => void
  setLevel: (level: AggregationLevel) => void
  setSelectedSegments: (segments: SegmentCode[]) => void
  setSelectedProvince: (province: string) => void
  setFromPeriod: (period: string) => void
  setToPeriod: (period: string) => void
  setSelectedRucs: (rucs: string[]) => void
  toggleRuc: (ruc: string) => void
  setSearchQuery: (q: string) => void
  setEntityPage: (page: number) => void
  resetFilters: () => void
}

const DEFAULT_SEGMENTS: SegmentCode[] = ["SEGMENTO_1", "SEGMENTO_2"]
const DEFAULT_RUCS: string[] = ["0190155722001", "0190115798001"]

export const useDashboardStore = create<DashboardState>((set) => ({
  activeView: "dashboard",
  selectedDimension: "all",
  isMobileMenuOpen: false,
  isSidebarCollapsed: false,

  selectedIndicator: "morosidad_cartera_total",
  level: "country",
  selectedSegments: DEFAULT_SEGMENTS,
  selectedProvince: "",
  fromPeriod: "2024-01",
  toPeriod: "2025-12",
  selectedRucs: DEFAULT_RUCS,

  searchQuery: "",
  entityPage: 1,

  setActiveView: (view) => set({ activeView: view }),
  setSelectedDimension: (dim) => set({ selectedDimension: dim }),
  setIsMobileMenuOpen: (open) => set({ isMobileMenuOpen: open }),
  setIsSidebarCollapsed: (collapsed) => set({ isSidebarCollapsed: collapsed }),
  setSelectedIndicator: (indicator) => set({ selectedIndicator: indicator }),
  setLevel: (level) => set({ level: level }),
  setSelectedSegments: (segments) => set({ selectedSegments: segments }),
  setSelectedProvince: (province) => set({ selectedProvince: province }),
  setFromPeriod: (from) => set({ fromPeriod: from }),
  setToPeriod: (to) => set({ toPeriod: to }),
  setSelectedRucs: (rucs) => set({ selectedRucs: rucs }),

  toggleRuc: (ruc) =>
    set((state) => {
      const exists = state.selectedRucs.includes(ruc)
      if (exists) {
        return { selectedRucs: state.selectedRucs.filter((r) => r !== ruc) }
      } else {
        if (state.selectedRucs.length >= 5) {
          // Límite normativo de 5 entidades simultáneas
          return state
        }
        return { selectedRucs: [...state.selectedRucs, ruc] }
      }
    }),

  setSearchQuery: (q) => set({ searchQuery: q, entityPage: 1 }),
  setEntityPage: (page) => set({ entityPage: page }),

  resetFilters: () =>
    set({
      selectedIndicator: "morosidad_cartera_total",
      level: "country",
      selectedSegments: DEFAULT_SEGMENTS,
      selectedProvince: "",
      fromPeriod: "2024-01",
      toPeriod: "2025-12",
      selectedRucs: DEFAULT_RUCS,
      searchQuery: "",
      entityPage: 1
    })
}))
