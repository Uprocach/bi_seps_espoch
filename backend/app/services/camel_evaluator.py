import json
import math
from pathlib import Path
from backend.app.core.config import settings
from backend.app.models.schemas import CamelEvaluation, TrafficLightStatus, Polarity

class CamelThresholdEvaluator:
    """Motor de Semáforo Regulatorio CAMEL Inteligente para el SFPS ecuatoriano."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or settings.CAMEL_THRESHOLDS_PATH
        self._config = self._load_config()

    def _load_config(self) -> dict:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Advertencia: No se pudo cargar camel_thresholds.json ({e}). Usando reglas por defecto.")
        return {"indicators": {}, "default_rule": {}}

    def evaluate(
        self,
        indicator_id: str,
        value: float | None,
        default_polarity: Polarity = "higher_is_better",
        indicator_name: str | None = None
    ) -> CamelEvaluation:
        """Evalúa un ratio financiero contra los umbrales normativos SEPS / COMF.
        
        Maneja rigurosamente casos de borde:
        - None / NaN / Inf: Retorna estado YELLOW/información pendiente.
        - Patrimonio negativo / Pérdidas: Retorna RED.
        - Morosidad cero (0.0): Retorna GREEN para indicadores lower_is_better.
        """
        # 1. Validación de casos borde numéricos
        if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
            return CamelEvaluation(
                status="YELLOW",
                value=None,
                normative_reference="SEPS v3.0",
                message="Dato no reportado o base contable insuficiente en el periodo.",
                polarity=default_polarity,
                threshold={}
            )

        val = float(value)
        cfg = self._config.get("indicators", {}).get(indicator_id)

        # 2. Si el indicador tiene configuración explícita en camel_thresholds.json
        if cfg:
            polarity: Polarity = cfg.get("polarity", default_polarity)
            thresholds = cfg.get("thresholds", {})
            norm_ref = cfg.get("normative_reference", "Normativa SEPS / COMF")
            messages = cfg.get("messages", {})

            # Caso especial: Neutral (e.g., Intermediación Financiera: óptimo en banda central)
            if polarity == "neutral":
                g_min = thresholds.get("green_min", 75.0)
                g_max = thresholds.get("green_max", 92.0)
                y_min = thresholds.get("yellow_min", 65.0)
                y_max = thresholds.get("yellow_max", 98.0)

                if g_min <= val <= g_max:
                    status: TrafficLightStatus = "GREEN"
                    msg = messages.get("green", f"Nivel óptimo en rango normativo ({g_min}% - {g_max}%).")
                elif y_min <= val <= y_max:
                    status: TrafficLightStatus = "YELLOW"
                    msg = messages.get("yellow", f"Alerta prudencial: Ratio fuera de la banda objetivo ({g_min}% - {g_max}%).")
                else:
                    status: TrafficLightStatus = "RED"
                    msg = messages.get("red", f"Desbalance crítico: Valor {val:.2f}% significativamente distante de la banda segura.")

                return CamelEvaluation(
                    status=status,
                    value=round(val, 4),
                    normative_reference=norm_ref,
                    message=msg,
                    polarity=polarity,
                    threshold=thresholds
                )

            # Caso: Menor es mejor (e.g. Morosidad, Gastos de operación, Activos improductivos)
            if polarity == "lower_is_better":
                # Borde: Valor negativo en morosidad o gastos es una anomalía contable en B11
                if val < 0:
                    return CamelEvaluation(
                        status="YELLOW",
                        value=round(val, 4),
                        normative_reference=norm_ref,
                        message=f"Anomalía contable: Saldo negativo inusual ({val:.2f}%) en indicador con polaridad inversa.",
                        polarity=polarity,
                        threshold=thresholds
                    )

                g_max = thresholds.get("green_max", 5.0)
                y_max = thresholds.get("yellow_max", 8.0)

                if val <= g_max + 1e-6:
                    status = "GREEN"
                    msg = messages.get("green", f"Valor óptimo y controlado ({val:.2f}% ≤ {g_max}%).")
                elif val <= y_max + 1e-6:
                    status = "YELLOW"
                    msg = messages.get("yellow", f"Alerta temprana: Indicador en zona de observación ({val:.2f}% > {g_max}%).")
                else:
                    status = "RED"
                    msg = messages.get("red", f"Incumplimiento crítico: Nivel de riesgo severo ({val:.2f}% > {y_max}%).")

                return CamelEvaluation(
                    status=status,
                    value=round(val, 4),
                    normative_reference=norm_ref,
                    message=msg,
                    polarity=polarity,
                    threshold=thresholds
                )

            # Caso: Mayor es mejor (e.g. Solvencia, Cobertura, Liquidez, ROA, ROE)
            g_min = thresholds.get("green_min", 100.0)
            y_min = thresholds.get("yellow_min", 80.0)

            # Borde: Valor negativo en solvencia, capital o rentabilidad es automáticamente crítico (Causal COMF 198/303)
            if val < 0:
                return CamelEvaluation(
                    status="RED",
                    value=round(val, 4),
                    normative_reference=norm_ref,
                    message=f"Situación patrimonial deficitaria o pérdidas operativas ({val:.2f}%). Causal prudencial crítica (COMF Art. 198/303).",
                    polarity=polarity,
                    threshold=thresholds
                )

            if val >= g_min - 1e-6:
                status = "GREEN"
                msg = messages.get("green", f"Cumple holgadamente el estándar normativo (≥ {g_min}%).")
            elif val >= y_min - 1e-6:
                status = "YELLOW"
                msg = messages.get("yellow", f"Alerta preventiva: Cobertura inferior a la meta óptima (entre {y_min}% y {g_min}%).")
            else:
                status = "RED"
                msg = messages.get("red", f"Déficit crítico normativo: Indicador bajo el umbral mínimo prudencial (< {y_min}%).")

            return CamelEvaluation(
                status=status,
                value=round(val, 4),
                normative_reference=norm_ref,
                message=msg,
                polarity=polarity,
                threshold=thresholds
            )

        # 3. Reglas heurísticas estándar si el indicador no tiene umbral regulatorio directo
        if default_polarity == "lower_is_better":
            # Si el valor es pequeño, tiende a ser verde
            if val <= 5.0:
                status = "GREEN"
                msg = "Dentro de parámetros deseables según polaridad."
            elif val <= 10.0:
                status = "YELLOW"
                msg = "En zona de advertencia según polaridad."
            else:
                status = "RED"
                msg = "Nivel elevado respecto al perfil de riesgo esperado."
        elif default_polarity == "higher_is_better":
            if val < 0:
                status = "RED"
                msg = "Rendimiento o balance negativo."
            elif val >= 50.0:
                status = "GREEN"
                msg = "Nivel favorable según polaridad."
            elif val >= 20.0:
                status = "YELLOW"
                msg = "Nivel intermedio en zona de observación."
            else:
                status = "RED"
                msg = "Nivel bajo respecto a la polaridad deseable."
        else:
            status = "YELLOW"
            msg = "Indicador de monitoreo de estructura de balance."

        return CamelEvaluation(
            status=status,
            value=round(val, 4),
            normative_reference="SEPS v3.0 (Heurística General)",
            message=msg,
            polarity=default_polarity,
            threshold={}
        )

# Instancia singleton del evaluador
camel_evaluator = CamelThresholdEvaluator()
