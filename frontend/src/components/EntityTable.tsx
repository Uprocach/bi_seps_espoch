import React from "react"
import { Search, Building2, TrendingUp, CheckCircle2, ChevronLeft, ChevronRight, Download, Plus, Check } from "lucide-react"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table"
import { formatCurrency } from "@/lib/utils"
import { exportEntitiesToCsv } from "@/lib/exportUtils"
import type { EntitySummary } from "@/services/apiClient"

interface EntityTableProps {
  entities: EntitySummary[]
  isLoading?: boolean
  searchQuery: string
  onSearchChange: (q: string) => void
  selectedRucs: string[]
  onToggleEntity: (ruc: string) => void
  currentPage: number
  totalPages: number
  totalItems: number
  onPageChange: (page: number) => void
  canExport?: boolean
}

export const EntityTable: React.FC<EntityTableProps> = ({
  entities,
  isLoading = false,
  searchQuery,
  onSearchChange,
  selectedRucs,
  onToggleEntity,
  currentPage,
  totalPages,
  totalItems,
  onPageChange,
  canExport = false
}) => {
  return (
    <Card className="border-slate-200/80 shadow-sm overflow-hidden print:border-none print:shadow-none">
      <CardHeader className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3">
        <div>
          <CardTitle className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-emerald-700" />
            <span>Directorio y Benchmark de Cooperativas</span>
          </CardTitle>
          <CardDescription className="text-xs text-slate-500">
            {totalItems} entidades supervisadas por la SEPS ordenadas por activos. Selecciona hasta 3 para comparar.
          </CardDescription>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto print:hidden">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Buscar por RUC o Razón Social..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9 h-9 text-xs"
            />
          </div>

          {canExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => exportEntitiesToCsv(entities)}
              className="h-9 text-xs gap-1.5 whitespace-nowrap text-slate-700"
            >
              <Download className="h-3.5 w-3.5 text-emerald-700" /> Directorio CSV
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12 text-center">#</TableHead>
              <TableHead>Cooperativa / Entidad</TableHead>
              <TableHead>Segmento</TableHead>
              <TableHead>Provincia</TableHead>
              <TableHead className="text-right">Activos (USD)</TableHead>
              <TableHead className="text-center w-36">Comparador</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-slate-400 text-xs">
                  Cargando entidades...
                </TableCell>
              </TableRow>
            ) : entities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-32 text-center text-slate-400 text-xs">
                  No se encontraron cooperativas que coincidan con la búsqueda.
                </TableCell>
              </TableRow>
            ) : (
              entities.map((ent, idx) => {
                const isSelected = selectedRucs.includes(ent.ruc)
                const rank = (currentPage - 1) * 15 + idx + 1

                return (
                  <TableRow
                    key={ent.ruc}
                    className={isSelected ? "bg-emerald-50/60 font-medium" : ""}
                  >
                    <TableCell className="text-center font-mono text-xs text-slate-400">
                      {rank}
                    </TableCell>

                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-semibold text-slate-900 text-xs line-clamp-1">
                          {ent.razon_social}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="font-mono text-[11px] text-slate-500">{ent.ruc}</span>
                          {ent.is_active && (
                            <span className="inline-flex items-center gap-0.5 text-[10px] text-emerald-700 bg-emerald-50 px-1 rounded">
                              <CheckCircle2 className="h-2.5 w-2.5" /> Activa
                            </span>
                          )}
                        </div>
                      </div>
                    </TableCell>

                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-medium border-slate-200">
                        {ent.segment.replace("SEGMENTO_", "Seg ").replace("_MUTUALISTA", " Mut")}
                      </Badge>
                    </TableCell>

                    <TableCell>
                      <span className="text-xs text-slate-600 font-medium">
                        {ent.province?.name || "-"}
                      </span>
                    </TableCell>

                    <TableCell className="text-right font-mono text-xs font-bold text-slate-900">
                      {formatCurrency(ent.total_assets_usd)}
                    </TableCell>

                    <TableCell className="text-center print:hidden">
                      <Button
                        size="sm"
                        variant={isSelected ? "default" : "outline"}
                        onClick={() => onToggleEntity(ent.ruc)}
                        className="h-7 text-[11px] px-2.5 gap-1"
                      >
                        {isSelected ? (
                          <>
                            <Check className="h-3 w-3" /> Comparando
                          </>
                        ) : (
                          <>
                            <Plus className="h-3 w-3" /> Comparar
                          </>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3 px-4 border-t border-slate-100 bg-slate-50/50 text-xs text-slate-600 print:hidden">
            <span>
              Página {currentPage} de {totalPages} ({totalItems} entidades)
            </span>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage <= 1}
                className="h-7 w-7 p-0"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="h-7 w-7 p-0"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
