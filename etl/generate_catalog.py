import json
import re

with open("data/raw/fichas_extracted.json", "r", encoding="utf-8") as f:
    fichas = json.load(f)

# Diccionario de correcciones ortográficas específicas
SPELL_REPLACEMENTS = [
    (r"\bCOMSUMO\b", "CONSUMO"),
    (r"\bComsumo\b", "Consumo"),
    (r"\bcomsumo\b", "consumo"),
    (r"\bMICROCREDITO\b", "MICROCRÉDITO"),
    (r"\bMicrocredito\b", "Microcrédito"),
    (r"\bmicrocredito\b", "microcrédito"),
    (r"\bPROPORCION\b", "PROPORCIÓN"),
    (r"\bProporcion\b", "Proporción"),
    (r"\bproporcion\b", "proporción"),
    (r"\bUTILIZACION\b", "UTILIZACIÓN"),
    (r"\bUtilizacion\b", "Utilización"),
    (r"\butilizacion\b", "utilización"),
    (r"\bCREDITO\b", "CRÉDITO"),
    (r"\bCredito\b", "Crédito"),
    (r"\bcredito\b", "crédito"),
    (r"\bCREDITOS\b", "CRÉDITOS"),
    (r"\bCreditos\b", "Créditos"),
    (r"\bcreditos\b", "créditos"),
    (r"\bINTERES\b", "INTERÉS"),
    (r"\bInteres\b", "Interés"),
    (r"\binteres\b", "interés"),
    (r"\bPUBLICO\b", "PÚBLICO"),
    (r"\bPublico\b", "Público"),
    (r"\bpublico\b", "público"),
    (r"\bPUBLICA\b", "PÚBLICA"),
    (r"\bPublica\b", "Pública"),
    (r"\bpublica\b", "pública"),
    (r"\bABSORCION\b", "ABSORCIÓN"),
    (r"\bAbsorcion\b", "Absorción"),
    (r"\babsorcion\b", "absorción"),
    (r"\bOPERACION\b", "OPERACIÓN"),
    (r"\bOperacion\b", "Operación"),
    (r"\boperacion\b", "operación"),
    (r"\bADMINISTRACION\b", "ADMINISTRACIÓN"),
    (r"\bAdministracion\b", "Administración"),
    (r"\badministracion\b", "administración"),
    (r"\bINTERMEDIACION\b", "INTERMEDIACIÓN"),
    (r"\bIntermediacion\b", "Intermediación"),
    (r"\bintermediacion\b", "intermediación"),
    (r"\bINFORMACION\b", "INFORMACIÓN"),
    (r"\bInformacion\b", "Información"),
    (r"\binformacion\b", "información"),
    (r"\bDEFINICION\b", "DEFINICIÓN"),
    (r"\bDefinicion\b", "Definición"),
    (r"\bdefinicion\b", "definición"),
    (r"\bCATEGORIA\b", "CATEGORÍA"),
    (r"\bCategoria\b", "Categoría"),
    (r"\bcategoria\b", "categoría"),
    (r"\bGRAFICO\b", "GRÁFICO"),
    (r"\bGrafico\b", "Gráfico"),
    (r"\bgrafico\b", "gráfico"),
    (r"\bGRAFICA\b", "GRÁFICA"),
    (r"\bGrafica\b", "Gráfica"),
    (r"\bgrafica\b", "gráfica"),
    (r"\bHISTORICA\b", "HISTÓRICA"),
    (r"\bHistorica\b", "Histórica"),
    (r"\bhistorica\b", "histórica"),
    (r"\bMETODOLOGICA\b", "METODOLÓGICA"),
    (r"\bMetodologica\b", "Metodológica"),
    (r"\bmetodologica\b", "metodológica"),
    (r"\bTECNICO\b", "TÉCNICO"),
    (r"\bTecnico\b", "Técnico"),
    (r"\btecnico\b", "técnico"),
    (r"\bTECNICA\b", "TÉCNICA"),
    (r"\bTecnica\b", "Técnica"),
    (r"\btecnica\b", "técnica"),
    (r"\bCALCULO\b", "CÁLCULO"),
    (r"\bCalculo\b", "Cálculo"),
    (r"\bcalculo\b", "cálculo"),
    (r"\bNUMERO\b", "NÚMERO"),
    (r"\bNumero\b", "Número"),
    (r"\bnumero\b", "número"),
    (r"\bLINEA\b", "LÍNEA"),
    (r"\bLinea\b", "Línea"),
    (r"\blinea\b", "línea"),
    (r"\bPOLITECNICA\b", "POLITÉCNICA"),
    (r"\bPolitecnica\b", "Politécnica"),
    (r"\bpolitecnica\b", "politécnica"),
    (r"\bINVESTIGACION\b", "INVESTIGACIÓN"),
    (r"\bInvestigacion\b", "Investigación"),
    (r"\binvestigacion\b", "investigación"),
    (r"\bSEMAFORO\b", "SEMÁFORO"),
    (r"\bSemaforo\b", "Semáforo"),
    (r"\bsemaforo\b", "semáforo"),
    (r"\bPADRON\b", "PADRÓN"),
    (r"\bPadron\b", "Padrón"),
    (r"\bpadron\b", "padrón"),
    (r"\bMODULO\b", "MÓDULO"),
    (r"\bModulo\b", "Módulo"),
    (r"\bmodulo\b", "módulo"),
]

def correct_spelling(text: str) -> str:
    res = text
    for pattern, replacement in SPELL_REPLACEMENTS:
        res = re.sub(pattern, replacement, res)
    return res

def format_title_spanish(name: str) -> str:
    corrected = correct_spelling(name)
    words = corrected.split()
    lower_words = {"de", "del", "con", "en", "a", "la", "el", "las", "los", "por", "sobre", "y", "o"}
    formatted = []
    for i, w in enumerate(words):
        w_lower = w.lower()
        if w.upper() in ["ROA", "ROE", "SEPS", "APR", "COMF"]:
            formatted.append(w.upper())
        elif i > 0 and w_lower in lower_words:
            formatted.append(w_lower)
        else:
            formatted.append(w.capitalize())
    return " ".join(formatted)

def get_category(num, name):
    name_u = name.upper()
    if 5 <= num <= 30:
        return "calidad_de_activos"
    elif num in [34, 35, 37, 38] or (39 <= num <= 51):
        return "rentabilidad"
    elif num in [1, 2, 53, 54, 58, 59, 60, 61, 62, 63]:
        return "capital"
    elif num in [3, 4, 52, 55]:
        return "liquidez"
    elif num in [31, 32, 33, 36]:
        return "manejo_administrativo"
    else:
        return "manejo_administrativo"

def is_public(num, category):
    public_fichas = {
        "calidad_de_activos": [5, 18, 9, 16],       # 4 public
        "rentabilidad": [35, 34, 38, 51],          # 4 public
        "capital": [1, 2, 53, 54],                 # 4 public
        "liquidez": [52, 4, 3, 55],                # 4 public
        "manejo_administrativo": [36, 31, 32, 33]  # 4 public
    }
    return num in public_fichas.get(category, [])

def is_live(num):
    return num in [5, 18, 9, 16, 35, 34, 38, 51, 1, 2, 53, 54, 52, 4, 3, 55, 36, 31, 32, 33]

def get_id(num, name):
    live_ids = {
        5: "morosidad_cartera_total",
        18: "cobertura_cartera_improductiva",
        35: "roa",
        34: "roe",
        1: "solvencia_patrimonial",
        52: "liquidez_inmediata",
        36: "intermediacion_financiera",
        31: "eficiencia_operativa"
    }
    if num in live_ids:
        return live_ids[num]
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    return f"seps_{num}_{slug}"[:40]

def get_polarity(num, name):
    name_u = name.upper()
    if "MOROSIDAD" in name_u or "IMPRODUCTIV" in name_u or "EFICIENCIA OPERATIVA" in name_u or "ABSORCI" in name_u or "COSTO" in name_u:
        return "lower_is_better"
    elif "INTERMEDIACI" in name_u:
        return "neutral"
    else:
        return "higher_is_better"

REGULATORY_THRESHOLDS = {
    1: "Mínimo legal COMF: ≥ 9.00% (Prudencial SEPS ≥ 14.00%)",
    2: "Referencial prudencial: < 5.00%",
    3: "Referencial prudencial: ≥ 80.00%",
    4: "Referencial prudencial: ≥ 100.00%",
    5: "Referencial prudencial: < 5.00%",
    6: "Referencial prudencial: < 4.50%",
    7: "Referencial prudencial: < 5.50%",
    8: "Referencial prudencial: < 4.00%",
    9: "Referencial prudencial: < 6.50%",
    10: "Referencial prudencial: < 5.00%",
    11: "Referencial prudencial: < 5.00%",
    12: "Referencial prudencial: < 5.50%",
    13: "Referencial prudencial: < 3.50%",
    14: "Referencial prudencial: < 5.00%",
    15: "Referencial prudencial: < 4.50%",
    16: "Referencial prudencial: < 5.50%",
    17: "Referencial prudencial: < 4.00%",
    18: "Mínimo regulatorio SEPS: ≥ 100.00%",
    19: "Mínimo regulatorio SEPS: ≥ 100.00%",
    20: "Mínimo regulatorio SEPS: ≥ 100.00%",
    21: "Mínimo regulatorio SEPS: ≥ 100.00%",
    22: "Mínimo regulatorio SEPS: ≥ 100.00%",
    23: "Mínimo regulatorio SEPS: ≥ 100.00%",
    24: "Mínimo regulatorio SEPS: ≥ 100.00%",
    25: "Mínimo regulatorio SEPS: ≥ 100.00%",
    26: "Mínimo regulatorio SEPS: ≥ 100.00%",
    27: "Mínimo regulatorio SEPS: ≥ 100.00%",
    28: "Mínimo regulatorio SEPS: ≥ 100.00%",
    29: "Mínimo regulatorio SEPS: ≥ 100.00%",
    30: "Mínimo regulatorio SEPS: ≥ 100.00%",
    31: "Límite prudencial deseable: < 5.00%",
    32: "Referencial de mercado: < 75.00%",
    33: "Referencial de mercado: < 35.00%",
    34: "Benchmark prudencial: ≥ 8.00%",
    35: "Benchmark prudencial: ≥ 1.00%",
    36: "Rango prudencial sano: 85.00% - 105.00%",
    37: "Referencial de mercado: ≥ 15.00%",
    38: "Referencial de mercado: 5.00% - 9.00%",
    39: "Tasa activa referencial: 10.00% - 14.00%",
    40: "Tasa activa referencial: 14.00% - 18.00%",
    41: "Tasa activa referencial: 14.00% - 18.00%",
    42: "Tasa activa referencial: 9.00% - 12.00%",
    43: "Tasa activa referencial: 18.00% - 24.00%",
    44: "Tasa activa referencial: 11.00% - 15.00%",
    45: "Tasa activa referencial: 11.00% - 15.00%",
    46: "Tasa activa referencial: 15.00% - 19.00%",
    47: "Tasa activa regulada: 4.99%",
    48: "Tasa activa regulada: 8.00% - 10.00%",
    49: "Referencial de cartera refinanciada",
    50: "Referencial de cartera reestructurada",
    51: "Tasa activa promedio ponderada: 12.00% - 16.00%",
    52: "Rango normativo SEPS: ≥ 18.00% - 25.00%",
    53: "Referencial prudencial: < 10.00%",
    54: "Referencial prudencial: < 15.00%",
    55: "Mínimo regulatorio: Superávit (> 0 USD)",
    58: "Componente patrimonial básico regulatorio",
    59: "Componente patrimonial complementario",
    60: "Cumplimiento del Patrimonio Técnico Requerido",
    61: "Activos y contingentes ponderados por riesgo",
    62: "Mínimo legal COMF (Art. 190): ≥ 9.00%",
    63: "Requerimiento de capital según segmento SEPS"
}

def get_short_name(num, name):
    if num == 5: return "Morosidad Total"
    if num == 18: return "Cobertura Problemática"
    if num == 9: return "Morosidad Microcrédito"
    if num == 16: return "Morosidad Consumo"
    if num == 35: return "ROA"
    if num == 34: return "ROE"
    if num == 38: return "Margen Intermediación"
    if num == 51: return "Rendimiento Cartera"
    if num == 1: return "Suficiencia Patrimonial"
    if num == 2: return "Activos Improductivos"
    if num == 53: return "Improd. / Patr. + Res."
    if num == 54: return "Improd. / Patrimonio"
    if num == 52: return "Liquidez Inmediata"
    if num == 4: return "Utilización Pasivo"
    if num == 3: return "Activos Productivos"
    if num == 55: return "Fondo Patrimonial FK"
    if num == 36: return "Intermediación Financiera"
    if num == 31: return "Eficiencia Operativa"
    if num == 32: return "Absorción Margen Neto"
    if num == 33: return "Eficiencia de Personal"
    
    clean = re.sub(r"^(MOROSIDAD DE CARTERA|COBERTURA DE LA CARTERA DE CRÉDITOS|COBERTURA DE LA CARTERA|RENDIMIENTO DE LA CARTERA DE CRÉDITO|RENDIMIENTO DE LA CARTERA DE|RENDIMIENTO DE LA CARTERA)\s*", "", name, flags=re.I)
    clean = clean.replace("POR VENCER", "").strip()
    clean = format_title_spanish(clean)
    if len(clean) > 28:
        clean = clean[:25] + "..."
    return clean

entries = []
for f in fichas:
    num = f["num"]
    raw_name = f["name"].strip()
    formatted_name = format_title_spanish(raw_name)
    cat = get_category(num, raw_name)
    pub = is_public(num, cat)
    live = is_live(num)
    pol = get_polarity(num, raw_name)
    ind_id = get_id(num, raw_name)
    short = get_short_name(num, raw_name)
    desc = correct_spelling(f["definition"]).replace('"', '\\"').strip()
    if not desc:
        desc = f"Ficha técnica oficial #{num} según Fichas Metodológicas V3.0 de la SEPS."
    form = correct_spelling(f["formula"]).replace('"', '\\"').strip()
    if not form:
        form = "Fórmula según Ficha Metodológica SEPS V3.0"

    threshold = REGULATORY_THRESHOLDS.get(num, "Referencial normativo SEPS V3.0")

    entries.append({
        "id": ind_id,
        "seps_ficha_number": num,
        "name": formatted_name,
        "short_name": short,
        "category": cat,
        "description": desc,
        "unit": "percent",
        "decimals": 2,
        "polarity": pol,
        "access": "public" if pub else "accredited",
        "is_live": live,
        "regulatory_threshold": threshold,
        "formula_display": form,
        "components_description": f"Ficha Metodológica Nº {num} (Página {f['page']} del documento oficial)"
    })

ts_content = """export type IndicatorCategory = 
  | "calidad_de_activos"
  | "rentabilidad"
  | "capital"
  | "liquidez"
  | "manejo_administrativo"

export type AccessLevel = "public" | "accredited"

export interface CatalogIndicator {
  id: string
  seps_ficha_number: number
  name: string
  short_name: string
  category: IndicatorCategory
  description: string
  unit: "percent" | "ratio" | "usd"
  decimals: number
  polarity: "higher_is_better" | "lower_is_better" | "neutral"
  access: AccessLevel
  is_live: boolean
  regulatory_threshold?: string
  normative_status?: string
  formula_display: string
  components_description: string
}

export const EXTENDED_CATALOG: CatalogIndicator[] = """ + json.dumps(entries, ensure_ascii=False, indent=2) + """;

export const CATEGORY_LABELS: Record<IndicatorCategory, { name: string; icon: string; color: string }> = {
  calidad_de_activos: {
    name: "Calidad de Activos & Cartera",
    icon: "ShieldAlert",
    color: "emerald"
  },
  rentabilidad: {
    name: "Rentabilidad & Desempeño",
    icon: "TrendingUp",
    color: "amber"
  },
  capital: {
    name: "Capital & Solvencia",
    icon: "Building",
    color: "teal"
  },
  liquidez: {
    name: "Liquidez & Fondos",
    icon: "Droplets",
    color: "cyan"
  },
  manejo_administrativo: {
    name: "Eficiencia & Gestión",
    icon: "Settings",
    color: "slate"
  }
}

export interface DimensionDefinition {
  id: IndicatorCategory
  name: string
  shortName: string
  description: string
  normativeFocus: string
  badge: string
}

export const CAMEL_DIMENSIONS: DimensionDefinition[] = [
  {
    id: "calidad_de_activos",
    name: "Calidad de Activos & Cartera",
    shortName: "Calidad Cartera",
    description: "Evaluación del riesgo crediticio, morosidad y cobertura de provisiones (Fichas 5 a 30).",
    normativeFocus: "Fichas SEPS #5 a #30 • 28 indicadores normativos",
    badge: "Activos"
  },
  {
    id: "rentabilidad",
    name: "Rentabilidad & Desempeño",
    shortName: "Rentabilidad",
    description: "Generación de excedentes netos, retornos ROA, ROE y rendimientos de cartera por vencer (Fichas 34 a 51).",
    normativeFocus: "Fichas SEPS #34 a #51 • 17 indicadores normativos",
    badge: "Excedentes"
  },
  {
    id: "capital",
    name: "Capital & Solvencia Patrimonial",
    shortName: "Solvencia",
    description: "Capacidad patrimonial para respaldar operaciones y solvencia técnica (Fichas 1, 2, 58 a 63).",
    normativeFocus: "Fichas SEPS #1, #2, #58 a #63 • 8 indicadores normativos",
    badge: "Solvencia"
  },
  {
    id: "liquidez",
    name: "Liquidez & Cobertura de Fondos",
    shortName: "Liquidez",
    description: "Disponibilidad de fondos y calce de obligaciones exigibles con el público (Fichas 3, 4, 52, 55).",
    normativeFocus: "Fichas SEPS #3, #4, #52, #55 • 4 indicadores normativos",
    badge: "Liquidez"
  },
  {
    id: "manejo_administrativo",
    name: "Eficiencia & Gestión Operativa",
    shortName: "Eficiencia",
    description: "Intermediación de fondos, contención de gastos de operación y costos de personal (Fichas 31 a 33, 36).",
    normativeFocus: "Fichas SEPS #31 a #33, #36 • 6 indicadores normativos",
    badge: "Operación"
  }
];
"""

with open("frontend/src/data/extendedCatalog.ts", "w", encoding="utf-8") as f:
    f.write(ts_content)

print(f"Generated extendedCatalog.ts with {len(entries)} indicators with full Spanish accents and thresholds!")
