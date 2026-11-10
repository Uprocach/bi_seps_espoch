import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "-"
  if (amount >= 1_000_000_000) {
    return `$${(amount / 1_000_000_000).toFixed(2)}B`
  }
  if (amount >= 1_000_000) {
    return `$${(amount / 1_000_000).toFixed(2)}M`
  }
  if (amount >= 1_000) {
    return `$${(amount / 1_000).toFixed(1)}k`
  }
  return `$${amount.toLocaleString("es-EC", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined) return "-"
  return `${value.toFixed(decimals)}%`
}

/**
 * Limpia y destaca el nombre comercial distintivo de una cooperativa
 * eliminando los prefijos genéricos largos (e.g. 'COOPERATIVA DE AHORRO Y CREDITO')
 * y sufijos ('LIMITADA', 'LTDA') para una lectura inmediata y sin recortes.
 */
export function formatCoopName(fullName: string | null | undefined): string {
  if (!fullName) return ""
  let name = fullName.trim()

  // Eliminar prefijos comunes del SFPS
  name = name.replace(
    /^(COOPERATIVA DE AHORRO Y CR[EÉ]DITO|MUTUALISTA DE AHORRO Y CR[EÉ]DITO PARA LA VIVIENDA|MUTUALISTA|CAJA CENTRAL|COOPERATIVA)\s+/i,
    ""
  )

  // Eliminar sufijos societarios
  name = name.replace(/\s+(LIMITADA|LTDA\.?|S\.A\.?)$/i, "")
  name = name.trim()

  if (!name) return fullName

  // Formatear mayúsculas a Title Case conservando acrónimos reconocidos
  if (name === name.toUpperCase()) {
    const acronyms = new Set(["JEP", "CREA", "OSCUS", "CACPE", "COOPMEGO", "FINANCOOP", "FEDECACES"])
    const smallWords = new Set(["de", "del", "la", "las", "el", "los", "y", "en"])

    const words = name.toLowerCase().split(/\s+/)
    name = words
      .map((w, idx) => {
        const upper = w.toUpperCase()
        if (acronyms.has(upper)) return upper
        if (idx > 0 && smallWords.has(w)) return w
        return w.charAt(0).toUpperCase() + w.slice(1)
      })
      .join(" ")
  }

  return name
}
