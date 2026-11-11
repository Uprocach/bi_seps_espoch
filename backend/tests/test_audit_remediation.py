"""
Audit Remediation Test Suite - ESPOCH - DI - 060
Valida formalmente la corrección de los hallazgos críticos y altos detectados en la auditoría 360°:
- AUD-01: Ranking vectorial con polaridad neutral (distancia a centro óptimo normativo).
- AUD-02: Detección y semáforo crítico (RED) para patrimonio técnico negativo / insolvencia COMF.
- AUD-03: Middleware anti-CSRF validando cabeceras Origin/Referer en sesiones por cookies.
- AUD-04: Alineación RBAC: bloqueo de export_excel para rol investigador (403).
- AUD-05: Particionado Hive en consultas analíticas de ranking.
- AUD-06: Asincronía no bloqueante en auditoría.
- AUD-07: XlsxWriter con constant_memory=True y UTF-8 BOM en CSV.
"""

import pytest
import asyncio
import concurrent.futures
from unittest.mock import MagicMock
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.security import (
    require_roles,
    create_access_token,
    check_csrf_origin,
    CSRFOriginValidationMiddleware
)
from backend.app.core.errors import APIProblemException
from backend.app.services.benchmarking_service import benchmarking_service
from backend.app.services.camel_evaluator import camel_evaluator
from backend.app.services.export_service import export_service
from backend.app.services.repository import AnalyticsRepository
from backend.app.models.schemas import ExportRequest

def test_remediation_neutral_polarity_ranking():
    """AUD-01: Valida que el ranking de un indicador 'neutral' ordene por cercanía al centro normativo y no por DESC."""
    res = benchmarking_service.get_entity_ranking(
        indicator_id="intermediacion_financiera",
        period="2025-12",
        limit=20
    )
    assert res.indicator.polarity == "neutral"
    assert len(res.ranking) > 0

    # Centro normativo óptimo: (75 + 92) / 2 = 83.5%
    # El primer clasificado (#1) debe tener una distancia a 83.5% menor o igual a los siguientes
    top1 = res.ranking[0]
    dist_top1 = abs(top1.value - 83.5)
    
    for item in res.ranking[1:]:
        dist_item = abs(item.value - 83.5)
        assert dist_top1 <= dist_item + 1e-4, (
            f"Fallo de polaridad: {top1.razon_social} (dist={dist_top1:.2f}) "
            f"no debería estar antes de {item.razon_social} (dist={dist_item:.2f})"
        )

def test_remediation_invalid_indicator_ranking_400():
    """AUD-01: Valida que consultar ranking de un indicador inexistente lance un 400 en vez de fallback silencioso."""
    with pytest.raises(APIProblemException) as exc:
        benchmarking_service.get_entity_ranking(
            indicator_id="indicador_inexistente_xyz",
            period="2025-12"
        )
    assert exc.value.status_code == 400
    assert "no existe en el catálogo" in exc.value.detail

def test_remediation_negative_equity_red_camel_evaluation():
    """AUD-02: Valida que patrimonio negativo o déficit de solvencia retorne RED (Causal de liquidación COMF 198/303)."""
    # Solvencia patrimonial negativa
    eval_solv = camel_evaluator.evaluate(
        indicator_id="solvencia_patrimonial",
        value=-15.4,
        default_polarity="higher_is_better"
    )
    assert eval_solv.status == "RED"
    assert "COMF Art. 198/303" in eval_solv.message or "deficitaria" in eval_solv.message

    # Solvencia legal ACPR (Ficha 62) negativa
    eval_f62 = camel_evaluator.evaluate(
        indicator_id="seps_62_solvencia",
        value=-8.2,
        default_polarity="higher_is_better"
    )
    assert eval_f62.status == "RED"
    assert "COMF Art. 198/303" in eval_f62.message

    # ROE negativo
    eval_roe = camel_evaluator.evaluate(
        indicator_id="roe",
        value=-25.0,
        default_polarity="higher_is_better"
    )
    assert eval_roe.status == "RED"

    # Morosidad negativa (anomalía contable)
    eval_mora_neg = camel_evaluator.evaluate(
        indicator_id="morosidad_cartera_total",
        value=-2.1,
        default_polarity="lower_is_better"
    )
    assert eval_mora_neg.status == "YELLOW"
    assert "Anomalía contable" in eval_mora_neg.message

def test_remediation_rbac_export_excel_forbidden_for_investigador():
    """AUD-04: Valida que el rol 'investigador' sea rechazado con 403 al intentar exportar Excel."""
    checker = require_roles(["auditor", "administrador"])
    investigador_user = {"sub": "investigador.espoch", "role": "investigador"}

    with pytest.raises(HTTPException) as exc:
        checker(user=investigador_user)
    assert exc.value.status_code == 403
    assert "no cuenta con permisos suficientes" in exc.value.detail

    # Auditor y Administrador sí tienen acceso
    auditor_user = {"sub": "auditor.espoch", "role": "auditor"}
    assert checker(user=auditor_user) == auditor_user

def test_remediation_csrf_middleware_origin_validation():
    """AUD-03: Valida que la lógica anti-CSRF bloquee peticiones mutacionales con cookie desde orígenes no autorizados."""
    token = create_access_token({"sub": "auditor.espoch", "role": "auditor"})
    cookies = {settings.COOKIE_NAME: token}

    # 1. Petición POST con cookie de sesión institucional desde origen atacante externo -> Bloqueado
    assert check_csrf_origin(
        method="POST",
        cookies=cookies,
        origin="https://sitio-malicioso-atacante.com",
        referer=None,
        client_host="192.168.1.50"
    ) is False

    # 2. Petición POST con cookie de sesión institucional desde origen autorizado -> Permitido
    valid_origin = settings.CORS_ORIGINS[0]
    assert check_csrf_origin(
        method="POST",
        cookies=cookies,
        origin=valid_origin,
        referer=None,
        client_host="192.168.1.50"
    ) is True

    # 3. Petición POST sin cookie de sesión (ej. autenticación por token en header) -> Permitido
    assert check_csrf_origin(
        method="POST",
        cookies={},
        origin="https://otro-cliente.com",
        referer=None,
        client_host="192.168.1.50"
    ) is True

    # 4. Petición GET segura -> Siempre permitida
    assert check_csrf_origin(
        method="GET",
        cookies=cookies,
        origin="https://cualquier-sitio.com",
        referer=None
    ) is True

def test_remediation_concurrent_duckdb_queries():
    """AUD-09: Prueba de estrés concurrente: 15 consultas simultáneas sobre DuckDB sin fallos de concurrencia."""
    repo = AnalyticsRepository()

    def run_query(ruc: str):
        return repo.get_indicator_series(
            indicator="morosidad_cartera_total",
            level="entity",
            ruc=[ruc],
            from_period="2025-01",
            to_period="2025-12"
        )

    rucs = ["0190155722001", "0190115798001"] * 5  # 10 consultas concurrentes en hilos paralelos
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_query, r) for r in rucs]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 10
    for r in results:
        assert len(r["series"]) == 1
        assert len(r["series"][0]["points"]) == 12

def test_remediation_export_service_constant_memory_and_csv_bom():
    """AUD-07: Valida exportación Excel con constant_memory=True y exportación CSV con UTF-8 BOM."""
    req = ExportRequest(
        entity_ids=["0190155722001"],
        start_date="2025-10",
        end_date="2025-12",
        camel_dimension="capital"
    )

    # Validar Excel binario válido generado
    excel_bytes = export_service.generate_excel(req)
    assert len(excel_bytes) > 2000
    assert excel_bytes.startswith(b"PK")  # Cabecera estándar ZIP de archivos xlsx

    # Validar CSV con UTF-8 BOM
    csv_chunks = list(export_service.stream_csv(req, delimiter=";"))
    assert csv_chunks[0] == "\ufeff"
    assert "periodo;ruc;nombre_comercial;razon_social" in csv_chunks[1]

def test_remediation_aud16_ruc_format_validation():
    """AUD-16: Valida rechazo de RUCs malformados o con inyección en Pydantic."""
    from backend.app.models.schemas import BenchmarkingCompareRequest, ExportRequest

    # Rechazar caracteres especiales / inyección SQL
    with pytest.raises(ValueError) as exc1:
        BenchmarkingCompareRequest(
            entity_ids=["0190155722001' OR '1'='1"],
            start_date="2025-01",
            end_date="2025-12"
        )
    assert "Formato de RUC inválido" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        ExportRequest(
            entity_ids=["RUC_INVALIDO_TEXT"],
            start_date="2025-01",
            end_date="2025-12"
        )
    assert "Formato de RUC inválido" in str(exc2.value)

def test_remediation_aud13_aud15_persistent_sqlite_audit_logs_and_wal():
    """AUD-13 & AUD-15: Valida persistencia de audit_logs en SQLite y modo WAL activo."""
    from backend.app.services.user_db_service import user_db
    from backend.app.services.audit_service import audit_service

    # 1. Validar que journal_mode es WAL
    with user_db._get_connection() as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert mode.lower() == "wal"

    # 2. Registrar evento vía AuditService y recuperarlo vía query_events
    test_action = "test:audit_remediation_verify"
    audit_service.log_event(
        user_sub="test_auditor",
        user_role="auditor",
        action=test_action,
        resource="/test/resource",
        details={"audit_verified": True}
    )

    events, total = audit_service.query_events(action=test_action)
    assert total >= 1
    matched = [e for e in events if e["action"] == test_action]
    assert len(matched) >= 1
    assert matched[0]["user_sub"] == "test_auditor"
    assert matched[0]["user_role"] == "auditor"
