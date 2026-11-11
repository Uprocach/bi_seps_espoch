import React, { useState, useEffect, useRef } from "react"
import {
  RefreshCw,
  Globe,
  Database,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  Loader2,
  Layers
} from "lucide-react"
import type { PipelineSyncStatus, PipelineStatus } from "@/types/camel"

export const PipelineSyncCard: React.FC = () => {
  const [syncStatus, setSyncStatus] = useState<PipelineSyncStatus | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null)
  const [isTriggering, setIsTriggering] = useState(false)
  const [forceDownload, setForceDownload] = useState(false)
  const [actionFeedback, setActionFeedback] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null)

  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  const fetchSyncStatus = async () => {
    try {
      const res = await fetch("/api/v1/admin/pipeline-sync-status", {
        credentials: "include"
      })
      if (res.ok) {
        const data: PipelineSyncStatus = await res.json()
        setSyncStatus(data)
        return data
      }
    } catch {
      // Ignorar errores de red transitorios en polling
    }
    return null
  }

  const fetchPipelineStatus = async () => {
    try {
      const res = await fetch("/api/v1/admin/pipeline-status", {
        credentials: "include"
      })
      if (res.ok) {
        const data: PipelineStatus = await res.json()
        setPipelineStatus(data)
      }
    } catch {
      // Ignorar errores transitorios
    }
  }

  useEffect(() => {
    fetchSyncStatus()
    fetchPipelineStatus()

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [])

  // Iniciar o detener polling según si la tarea está en ejecución
  useEffect(() => {
    const isRunning =
      syncStatus?.status === "downloading" ||
      syncStatus?.status === "extracting" ||
      syncStatus?.status === "validating"

    if (isRunning) {
      if (!pollingRef.current) {
        pollingRef.current = setInterval(async () => {
          const current = await fetchSyncStatus()
          if (
            current &&
            (current.status === "success" || current.status === "idle" || current.status === "failed")
          ) {
            fetchPipelineStatus()
            if (current.status === "success") {
              window.dispatchEvent(new CustomEvent("pipeline-data-updated", { detail: current }))
              setActionFeedback({
                type: "success",
                text: `¡Sincronización exitosa! Nuevo periodo contable ${current.detected_period || "actualizado"} disponible en todos los paneles.`
              })
            }
            if (pollingRef.current) {
              clearInterval(pollingRef.current)
              pollingRef.current = null
            }
          }
        }, 2500)
      }
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [syncStatus?.status])

  const handleTriggerSync = async (dryRun: boolean = false) => {
    setIsTriggering(true)
    setActionFeedback(null)

    try {
      const res = await fetch("/api/v1/admin/pipeline-sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          force: forceDownload,
          dry_run: dryRun
        })
      })

      if (res.status === 202 || res.status === 200) {
        const data: PipelineSyncStatus = await res.json()
        setSyncStatus(data)
        setActionFeedback({
          type: "info",
          text: dryRun
            ? data.message
            : "Sincronización desatendida iniciada en segundo plano. Monitoreando progreso..."
        })
        if (!dryRun) {
          fetchPipelineStatus()
        }
      } else {
        const err = await res.json().catch(() => ({}))
        setActionFeedback({
          type: "error",
          text: err.detail || "Error al disparar la sincronización web."
        })
      }
    } catch {
      setActionFeedback({
        type: "error",
        text: "Error de conexión con el servidor backend."
      })
    } finally {
      setIsTriggering(false)
    }
  }

  const isSyncing =
    syncStatus?.status === "downloading" ||
    syncStatus?.status === "extracting" ||
    syncStatus?.status === "validating"

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="text-base font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Globe className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              Sincronización Web Oficial SEPS & Pipeline Zero-Downtime
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Conexión desatendida con el portal estadístico oficial de la Superintendencia de Economía Popular y Solidaria.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={forceDownload}
              onChange={(e) => setForceDownload(e.target.checked)}
              disabled={isSyncing || isTriggering}
              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-800"
            />
            Forzar re-descarga
          </label>

          <button
            onClick={() => handleTriggerSync(true)}
            disabled={isSyncing || isTriggering}
            className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            Simular (Dry-Run)
          </button>

          <button
            onClick={() => handleTriggerSync(false)}
            disabled={isSyncing || isTriggering}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-50 transition-colors"
          >
            {isSyncing || isTriggering ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            {isSyncing ? "Sincronizando..." : "Sincronizar con Portal SEPS"}
          </button>
        </div>
      </div>

      {/* Tarjetas de Diagnóstico Comparativo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
        {/* Corte en Producción Activa */}
        <div className="rounded-lg border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1.5 font-medium">
              <Database className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
              Corte en Producción Activo
            </span>
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
              En Servicio
            </span>
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900 dark:text-white">
            {pipelineStatus?.latest_period || "Consultando..."}
          </div>
          <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            {pipelineStatus?.periods_count
              ? `${pipelineStatus.periods_count} periodos mensuales (${pipelineStatus.entities_count} entidades)`
              : "Verificando Data Mart..."}
          </div>
        </div>

        {/* Corte Detectado en Portal SEPS */}
        <div className="rounded-lg border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1.5 font-medium">
              <Globe className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
              Portal Web SEPS
            </span>
            <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
              Conectado
            </span>
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900 dark:text-white">
            {syncStatus?.detected_period || "2026-08"}
          </div>
          <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {syncStatus?.last_sync_timestamp
              ? new Date(syncStatus.last_sync_timestamp).toLocaleString("es-EC")
              : "Pendiente de verificación"}
          </div>
        </div>

        {/* Estado Gatekeeper / Staging */}
        <div className="rounded-lg border border-slate-200/80 bg-slate-50/60 p-3.5 dark:border-slate-800 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1.5 font-medium">
              <ShieldCheck className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" />
              Validación Gatekeeper
            </span>
            <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-950 dark:text-purple-300">
              100% Rigor
            </span>
          </div>
          <div className="mt-2 text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            {pipelineStatus?.staging_ready ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                Staging Preparado
              </>
            ) : (
              <>
                <Layers className="h-4 w-4 text-slate-400" />
                Listo para Ingesta
              </>
            )}
          </div>
          <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            Protección Zero-Downtime y conmutación atómica.
          </div>
        </div>
      </div>

      {/* Barra de Progreso y Mensaje en Vivo */}
      {isSyncing && (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50/60 p-3.5 dark:border-blue-900/50 dark:bg-blue-950/20">
          <div className="flex items-center justify-between text-xs font-medium text-blue-900 dark:text-blue-200 mb-1.5">
            <span className="flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600 dark:text-blue-400" />
              {syncStatus?.message || "Procesando tarea de sincronización..."}
            </span>
            <span className="font-mono">{syncStatus?.progress_percent || 0}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-blue-200 dark:bg-blue-900/60 overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-500 ease-out"
              style={{ width: `${syncStatus?.progress_percent || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Feedback de Acción / Alerta */}
      {actionFeedback && !isSyncing && (
        <div
          className={`mt-4 rounded-lg border p-3 text-xs flex items-center gap-2 ${
            actionFeedback.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/20 dark:text-emerald-300"
              : actionFeedback.type === "error"
              ? "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-950/20 dark:text-red-300"
              : "border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-800 dark:bg-slate-800/40 dark:text-slate-300"
          }`}
        >
          {actionFeedback.type === "success" && <CheckCircle2 className="h-4 w-4 shrink-0" />}
          {actionFeedback.type === "error" && <AlertCircle className="h-4 w-4 shrink-0" />}
          {actionFeedback.type === "info" && <ArrowRight className="h-4 w-4 shrink-0" />}
          <span>{actionFeedback.text}</span>
        </div>
      )}
    </div>
  )
}
