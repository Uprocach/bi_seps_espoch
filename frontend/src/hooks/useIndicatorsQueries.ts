/**
 * Hooks de React Query (TanStack Query) para el Sistema de Indicadores SFPS
 * Centraliza la caché en memoria, revalidación reactiva y estados de carga/error.
 */

import { useQuery } from "@tanstack/react-query"
import {
  fetchMetadataFilters,
  fetchIndicatorSeries,
  fetchEntities,
  fetchBenchmarkingCompare,
  fetchAuditLogs,
  fetchPipelineStatus,
  fetchPipelineSyncStatus,
  type IndicatorSeriesParams,
  type ListEntitiesParams,
  type BenchmarkingCompareRequest
} from "@/services/httpClient"

export function useMetadataFiltersQuery() {
  return useQuery({
    queryKey: ["metadataFilters"],
    queryFn: () => fetchMetadataFilters(),
    staleTime: 60 * 60 * 1000
  })
}

export function useIndicatorSeriesQuery(params: IndicatorSeriesParams, enabled = true) {
  return useQuery({
    queryKey: ["indicatorSeries", params],
    queryFn: () => fetchIndicatorSeries(params),
    enabled: enabled && Boolean(params.indicator),
    staleTime: 5 * 60 * 1000
  })
}

export function useEntitiesQuery(params: ListEntitiesParams = {}) {
  return useQuery({
    queryKey: ["entities", params],
    queryFn: () => fetchEntities(params),
    staleTime: 10 * 60 * 1000
  })
}

export function useBenchmarkingCompareQuery(payload: BenchmarkingCompareRequest, enabled = true) {
  return useQuery({
    queryKey: ["benchmarkingCompare", payload],
    queryFn: () => fetchBenchmarkingCompare(payload),
    enabled: enabled && payload.entity_ids.length > 0,
    staleTime: 5 * 60 * 1000
  })
}

export function useAuditLogsQuery(params: Parameters<typeof fetchAuditLogs>[0] = {}, enabled = true) {
  return useQuery({
    queryKey: ["auditLogs", params],
    queryFn: () => fetchAuditLogs(params),
    enabled
  })
}

export function usePipelineStatusQuery() {
  return useQuery({
    queryKey: ["pipelineStatus"],
    queryFn: () => fetchPipelineStatus(),
    refetchInterval: 30000
  })
}

export function usePipelineSyncStatusQuery(enabled = false) {
  return useQuery({
    queryKey: ["pipelineSyncStatus"],
    queryFn: () => fetchPipelineSyncStatus(),
    refetchInterval: enabled ? 2000 : false
  })
}
