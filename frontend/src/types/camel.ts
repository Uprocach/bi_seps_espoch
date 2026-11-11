import type { EntitySummary, IndicatorMeta } from "@/services/apiClient"

export type Role = "public" | "investigador" | "auditor" | "administrador"

export type CamelDimension =
  | "capital"
  | "calidad_de_activos"
  | "manejo_administrativo"
  | "rentabilidad"
  | "liquidez"

export type TrafficLightStatus = "GREEN" | "YELLOW" | "RED"

export interface CamelEvaluation {
  status: TrafficLightStatus
  value: number | null
  normative_reference?: string | null
  message: string
  polarity?: "higher_is_better" | "lower_is_better" | "neutral"
  threshold?: Record<string, unknown>
}

export interface BenchmarkingIndicatorRow {
  indicator_id: string
  indicator_name: string
  dimension: string
  unit: string
  polarity: "higher_is_better" | "lower_is_better" | "neutral"
  seps_ficha_number?: number | null
  entity_values: Record<string, number | null>
  entity_evaluations: Record<string, CamelEvaluation>
  segment1_baseline: number | null
  country_baseline: number | null
}

export interface BenchmarkingSeriesPoint {
  period: string
  entity_values: Record<string, number | null>
  segment1_baseline?: number | null
  country_baseline?: number | null
}

export interface BenchmarkingCompareRequest {
  entity_ids: string[]
  start_date: string
  end_date: string
  camel_dimension?: CamelDimension
}

export interface BenchmarkingCompareResponse {
  entities: EntitySummary[]
  start_date: string
  end_date: string
  camel_dimension?: string | null
  indicators: BenchmarkingIndicatorRow[]
  time_series: Record<string, BenchmarkingSeriesPoint[]>
  total_indicators: number
  generated_at: string
}

export interface ExportRequestPayload {
  entity_ids: string[]
  start_date: string
  end_date: string
  camel_dimension?: CamelDimension
}

export interface UserProfile {
  sub: string
  role: Role
  name: string
  email: string
  permissions: string[]
  authenticated: boolean
  must_change_password?: boolean
}

export interface AdminUserListItem {
  id: number
  username: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  must_change_password: boolean
  created_at: string
  last_login_at?: string | null
}

export interface AdminUsersListResponse {
  users: AdminUserListItem[]
  total: number
}

export interface BulkImportItem {
  username?: string
  email?: string
  full_name: string
  role: Role
  password?: string
}

export interface BulkImportResponse {
  imported_count: number
  skipped_count: number
  created_users: Array<{
    id: number
    username: string
    email: string
    full_name: string
    role: string
    initial_password: string
  }>
  errors: string[]
}

export interface EntityRankingItem {
  rank: number
  national_rank?: number | null
  ruc: string
  razon_social: string
  segment: string
  province?: string | null
  total_assets_usd?: number | null
  value: number
  camel_evaluation: CamelEvaluation
  diff_country?: number | null
  diff_segment1?: number | null
}

export interface BenchmarkingRankingResponse {
  indicator: IndicatorMeta
  period: string
  segment_filter?: string | null
  province_filter?: string | null
  selected_rucs?: string[] | null
  segment1_baseline?: number | null
  country_baseline?: number | null
  ranking: EntityRankingItem[]
  total_ranked: number
  generated_at: string
}

export interface PipelineSyncStatus {
  status: "idle" | "downloading" | "extracting" | "validating" | "success" | "failed"
  progress_percent: number
  message: string
  detected_period?: string | null
  last_sync_timestamp?: string | null
  error_message?: string | null
}

export interface PipelineStatus {
  status: string
  active_mart_dir: string
  latest_period: string
  data_as_of: string
  periods_count: number
  entities_count: number
  staging_ready: boolean
  last_switch_timestamp?: string | null
}

