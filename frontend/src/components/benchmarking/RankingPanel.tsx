import React from "react"
import {
  Award,
  Check,
  Loader2,
  MapPin,
  Medal,
  Plus,
  RotateCcw,
  Search,
  Trophy,
  Users,
  X
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { useBenchmarkingWorkbench } from "@/hooks/useBenchmarkingWorkbench"
import { TrafficLightBadge } from "@/components/benchmarking/TrafficLightBadge"
import { formatCoopName, formatIndicatorValue } from "@/lib/utils"

interface RankingPanelProps {
  workbench: ReturnType<typeof useBenchmarkingWorkbench>
}

export const RankingPanel: React.FC<RankingPanelProps> = ({ workbench }) => {
  const {
    selectedRucs,
    activeChartIndicator,
    setActiveChartIndicator,
    rankingSegment,
    rankingProvince,
    rankingSelectedRucs,
    setRankingSelectedRucs,
    isPeerPickerOpen,
    setIsPeerPickerOpen,
    peerSearchQuery,
    setPeerSearchQuery,
    fullEntityCatalog,
    dynamicSegmentCounts,
    dynamicProvinceOptions,
    peerCandidates,
    benchmarkData,
    rankingData,
    isLoadingRanking,
    isFetchingRanking,
    rankingError,
    handleProvinceChange,
    handleSegmentChange,
    handleAddEntity,
    handleRemoveEntity,
    handleToggleRankingPeer
  } = workbench

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      <div className="p-4 bg-white border border-slate-200/80 rounded-xl shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Trophy className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-slate-900">
                Ranking Nacional del SFPS • {rankingData?.indicator.name || "Ratio Seleccionado"}
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Posición macroprudencial según la ficha metodológica oficial{" "}
              <strong className="text-slate-700">
                SEPS v3.0 (
                {rankingData?.indicator.seps_ficha_number
                  ? `Ficha ${rankingData.indicator.seps_ficha_number}`
                  : "CAMEL"}
                )
              </strong>
              .
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Ficha:</span>
            <select
              value={activeChartIndicator}
              onChange={(e) => setActiveChartIndicator(e.target.value)}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-600 max-w-xs font-medium"
            >
              {benchmarkData?.indicators?.map((ind) => (
                <option key={ind.indicator_id} value={ind.indicator_id}>
                  {ind.seps_ficha_number ? `Ficha ${ind.seps_ficha_number}: ` : ""}
                  {ind.indicator_name}
                </option>
              )) || (
                <option value="morosidad_cartera_total">
                  Ficha 01: Morosidad de Cartera Total
                </option>
              )}
            </select>
          </div>
        </div>

        <div className="pt-3 border-t border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap text-xs">
            <div className="flex items-center gap-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-700" />
              <span className="font-semibold text-slate-600">Provincia:</span>
              <select
                value={rankingProvince}
                onChange={(e) => handleProvinceChange(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-800 focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
              >
                <option value="all">
                  Todas las Provincias ({dynamicProvinceOptions.reduce((a, b) => a + b.count, 0)})
                </option>
                {dynamicProvinceOptions.map((prov) => (
                  <option key={prov.name} value={prov.name}>
                    {prov.name} ({prov.count})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-1 overflow-x-auto text-[11px] ml-1">
              {[
                { id: "all", label: `Todos (${dynamicSegmentCounts.all})` },
                {
                  id: "SEGMENTO_1",
                  label: `Seg 1 (${dynamicSegmentCounts.SEGMENTO_1})`,
                  disabled: dynamicSegmentCounts.SEGMENTO_1 === 0
                },
                {
                  id: "SEGMENTO_2",
                  label: `Seg 2 (${dynamicSegmentCounts.SEGMENTO_2})`,
                  disabled: dynamicSegmentCounts.SEGMENTO_2 === 0
                },
                {
                  id: "SEGMENTO_3",
                  label: `Seg 3 (${dynamicSegmentCounts.SEGMENTO_3})`,
                  disabled: dynamicSegmentCounts.SEGMENTO_3 === 0
                }
              ].map((seg) => (
                <button
                  key={seg.id}
                  disabled={seg.disabled}
                  onClick={() => handleSegmentChange(seg.id)}
                  className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                    rankingSegment === seg.id
                      ? "bg-emerald-700 text-white shadow-xs font-bold"
                      : seg.disabled
                      ? "bg-slate-50 text-slate-300 cursor-not-allowed"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {seg.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsPeerPickerOpen(true)}
              className={`text-xs gap-1.5 h-8 border ${
                rankingSelectedRucs.length > 0
                  ? "border-emerald-500 bg-emerald-50 text-emerald-800 font-bold"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              <Users className="w-3.5 h-3.5 text-emerald-700" />
              <span>Grupo de Pares ({rankingSelectedRucs.length}/10)</span>
            </Button>

            {rankingSelectedRucs.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setRankingSelectedRucs([])}
                className="text-[11px] h-8 px-2 text-rose-600 hover:bg-rose-50 hover:text-rose-700 gap-1"
                title="Limpiar filtro de cooperativas específicas"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Ver Todos</span>
              </Button>
            )}
          </div>
        </div>

        {rankingSelectedRucs.length > 0 && (
          <div className="p-2.5 bg-emerald-50/60 border border-emerald-200/80 rounded-lg flex items-center justify-between flex-wrap gap-2 text-xs">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="font-bold text-emerald-900 text-[11px] uppercase tracking-wider">
                Contraste entre Seleccionadas:
              </span>
              {rankingSelectedRucs.map((ruc) => {
                const ent = fullEntityCatalog.find((e) => e.ruc === ruc)
                const cleanName = ent ? formatCoopName(ent.razon_social) : ruc
                return (
                  <span
                    key={ruc}
                    className="inline-flex items-center gap-1 pl-2 pr-1.5 py-0.5 rounded-md bg-white border border-emerald-300 text-emerald-900 text-[11px] font-semibold shadow-2xs"
                  >
                    <span>{cleanName}</span>
                    <button
                      onClick={() => handleToggleRankingPeer(ruc)}
                      className="text-slate-400 hover:text-rose-600 rounded"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )
              })}
            </div>
            <span className="text-[11px] text-emerald-700 font-medium">
              Ranking focalizado exclusivo ({rankingSelectedRucs.length} COACs)
            </span>
          </div>
        )}
      </div>

      {isPeerPickerOpen && (
        <div
          className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setIsPeerPickerOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full flex flex-col max-h-[80vh] overflow-hidden animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-emerald-700" />
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    Seleccionar Grupo de Pares para Ranking
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    Elige de 2 a 10 cooperativas para conocer el ranking exclusivo entre ellas (
                    {rankingSelectedRucs.length}/10 seleccionadas).
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsPeerPickerOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 border-b border-slate-100">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Buscar por nombre, RUC o provincia..."
                  value={peerSearchQuery}
                  onChange={(e) => setPeerSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-600 font-medium"
                  autoFocus
                />
              </div>
            </div>

            <div className="overflow-y-auto flex-1 divide-y divide-slate-100 p-2 text-xs">
              {peerCandidates.map((cand) => {
                const isChecked = rankingSelectedRucs.includes(cand.ruc)
                const cleanName = formatCoopName(cand.razon_social)
                return (
                  <div
                    key={cand.ruc}
                    onClick={() => handleToggleRankingPeer(cand.ruc)}
                    className={`p-2.5 rounded-lg flex items-center justify-between cursor-pointer transition-colors ${
                      isChecked ? "bg-emerald-50/80 font-bold" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="min-w-0 pr-2">
                      <p className="text-xs text-slate-900 truncate">{cleanName}</p>
                      <p className="text-[10px] text-slate-400 truncate">
                        {cand.ruc} • {cand.segment} • {cand.province?.name || "Ecuador"}
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500"
                    />
                  </div>
                )
              })}
            </div>

            <div className="p-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                {rankingSelectedRucs.length} cooperativas seleccionadas para ranking
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setRankingSelectedRucs([])}
                  className="text-xs h-7"
                >
                  Limpiar
                </Button>
                <Button
                  size="sm"
                  onClick={() => setIsPeerPickerOpen(false)}
                  className="text-xs h-7 bg-emerald-700 hover:bg-emerald-800 text-white"
                >
                  Aplicar ({rankingSelectedRucs.length})
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="border-slate-200/80 bg-white shadow-xs">
          <CardContent className="p-3">
            <p className="text-[10px] text-slate-400 uppercase font-semibold">
              Criterio de Evaluación
            </p>
            <p className="text-xs font-bold text-slate-800 mt-1">
              {rankingData?.indicator.polarity === "lower_is_better"
                ? "Menor Valor = Mejor Puesto"
                : "Mayor Valor = Mejor Puesto"}
            </p>
            <p className="text-[10px] text-emerald-700 font-medium mt-0.5">
              {rankingData?.indicator.polarity === "lower_is_better"
                ? "Menor índice de mora / carga"
                : "Mayor solvencia y rentabilidad"}
            </p>
          </CardContent>
        </Card>

        <Card className="border-slate-200/80 bg-white shadow-xs">
          <CardContent className="p-3">
            <p className="text-[10px] text-slate-400 uppercase font-semibold">
              Línea Base Segmento 1
            </p>
            <p className="text-base font-bold font-mono text-slate-900 mt-1">
              {formatIndicatorValue(rankingData?.segment1_baseline, rankingData?.indicator?.unit)}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Referencia de grandes cooperativas</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200/80 bg-white shadow-xs">
          <CardContent className="p-3">
            <p className="text-[10px] text-slate-400 uppercase font-semibold">
              Promedio Nacional SFPS
            </p>
            <p className="text-base font-bold font-mono text-slate-900 mt-1">
              {formatIndicatorValue(rankingData?.country_baseline, rankingData?.indicator?.unit)}
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">Media consolidada país</p>
          </CardContent>
        </Card>

        <Card className="border-slate-200/80 bg-white shadow-xs">
          <CardContent className="p-3">
            <p className="text-[10px] text-slate-400 uppercase font-semibold">
              Entidades Clasificadas
            </p>
            <p className="text-base font-bold font-mono text-emerald-800 mt-1">
              {rankingData?.ranking.length || 0} COACs
            </p>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Corte: {rankingData?.period || workbench.toPeriod}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="bg-white border border-slate-200/80 rounded-xl shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th className="py-3 px-3 text-center w-16">Pos.</th>
                <th className="py-3 px-3">Cooperativa / Mutualista</th>
                <th className="py-3 px-3">Segmento</th>
                <th className="py-3 px-3">Provincia</th>
                <th className="py-3 px-3 text-right">Activos Totales</th>
                <th className="py-3 px-3 text-right">Valor</th>
                <th className="py-3 px-3 text-center">Semáforo SEPS</th>
                <th className="py-3 px-3 text-right">vs País</th>
                <th className="py-3 px-3 text-center">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoadingRanking || isFetchingRanking ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto text-emerald-700 mb-2" />
                    Calculando ranking nacional sobre cubos DuckDB...
                  </td>
                </tr>
              ) : rankingError ? (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-rose-600">
                    Error cargando el ranking:{" "}
                    {rankingError instanceof Error ? rankingError.message : "Error de servidor"}
                  </td>
                </tr>
              ) : (rankingData?.ranking.length || 0) === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    No hay cooperativas clasificadas con los filtros actuales.
                  </td>
                </tr>
              ) : (
                rankingData?.ranking.map((row: any) => {
                  const isSelected = selectedRucs.includes(row.ruc)
                  const cleanName = formatCoopName(row.razon_social)
                  const segBadge =
                    row.segment === "SEGMENTO_1"
                      ? "Segmento 1"
                      : row.segment === "SEGMENTO_2"
                      ? "Segmento 2"
                      : row.segment === "SEGMENTO_3"
                      ? "Segmento 3"
                      : "Mutualista"

                  let rankBadge = (
                    <div className="flex flex-col items-center">
                      <span className="font-mono font-bold text-slate-700">#{row.rank}</span>
                      {row.national_rank && row.national_rank !== row.rank && (
                        <span className="text-[9px] text-slate-400 font-mono">
                          (#{row.national_rank} nac.)
                        </span>
                      )}
                    </div>
                  )

                  if (row.rank === 1) {
                    rankBadge = (
                      <div className="flex flex-col items-center">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold border border-amber-300">
                          <Trophy className="w-3 h-3 text-amber-600" /> #1
                        </span>
                        {row.national_rank && row.national_rank !== 1 && (
                          <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                            (#{row.national_rank} nac.)
                          </span>
                        )}
                      </div>
                    )
                  } else if (row.rank === 2) {
                    rankBadge = (
                      <div className="flex flex-col items-center">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-200 text-slate-800 font-bold border border-slate-300">
                          <Medal className="w-3 h-3 text-slate-600" /> #2
                        </span>
                        {row.national_rank && row.national_rank !== 2 && (
                          <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                            (#{row.national_rank} nac.)
                          </span>
                        )}
                      </div>
                    )
                  } else if (row.rank === 3) {
                    rankBadge = (
                      <div className="flex flex-col items-center">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 font-bold border border-amber-200">
                          <Award className="w-3 h-3 text-amber-700" /> #3
                        </span>
                        {row.national_rank && row.national_rank !== 3 && (
                          <span className="text-[9px] text-slate-400 font-mono mt-0.5">
                            (#{row.national_rank} nac.)
                          </span>
                        )}
                      </div>
                    )
                  }

                  const assetsFormatted = row.total_assets_usd
                    ? `$${(row.total_assets_usd / 1_000_000).toFixed(1)}M`
                    : "N/D"

                  const diffCountry = row.diff_country
                  const isDiffPositive =
                    diffCountry !== null && diffCountry !== undefined && diffCountry > 0

                  return (
                    <tr
                      key={row.ruc}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isSelected ? "bg-emerald-50/30" : ""
                      }`}
                    >
                      <td className="py-2.5 px-3 text-center">{rankBadge}</td>
                      <td className="py-2.5 px-3">
                        <p className="font-bold text-slate-900" title={row.razon_social}>
                          {cleanName}
                        </p>
                        <p className="text-[10px] text-slate-400 font-mono">
                          RUC: {row.ruc.slice(0, 10)}
                        </p>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                          {segBadge}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{row.province || "Ecuador"}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-600">
                        {assetsFormatted}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                        {formatIndicatorValue(row.value, rankingData?.indicator?.unit)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <TrafficLightBadge
                          evalItem={row.camel_evaluation}
                          value={row.value}
                          unit={rankingData?.indicator?.unit || "percent"}
                        />
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-xs">
                        {diffCountry !== null && diffCountry !== undefined ? (
                          <span
                            className={
                              (rankingData?.indicator.polarity === "lower_is_better" &&
                                !isDiffPositive) ||
                              (rankingData?.indicator.polarity === "higher_is_better" &&
                                isDiffPositive)
                                ? "text-emerald-700 font-semibold"
                                : "text-rose-600 font-semibold"
                            }
                          >
                            {formatIndicatorValue(diffCountry, rankingData?.indicator?.unit, {
                              signed: true
                            })}
                          </span>
                        ) : (
                          "N/D"
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {isSelected ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRemoveEntity(row.ruc)}
                            className="text-[10px] h-7 px-2 border-emerald-300 bg-emerald-50 text-emerald-800 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-300 gap-1"
                            title="En contraste. Haz clic para remover"
                          >
                            <Check className="w-3 h-3" />
                            <span>En Contraste</span>
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleAddEntity(row.ruc)}
                            disabled={selectedRucs.length >= 5}
                            className="text-[10px] h-7 px-2 border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 text-slate-700 gap-1"
                            title="Añadir cooperativa al comparador de benchmarking"
                          >
                            <Plus className="w-3 h-3 text-emerald-700" />
                            <span>Comparar</span>
                          </Button>
                        )}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
