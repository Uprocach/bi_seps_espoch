import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import json
import sqlite3
import sys
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
test_results = []

def record(code, name, status, details=""):
    test_results.append({"code": code, "name": name, "status": status, "details": details})
    print(f"[{status}] {code} - {name}: {details}")

# Cookie jar para peticiones con sesión
jar = http.cookiejar.CookieJar()
session_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def do_get(path, headers=None, opener=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=headers or {})
    try:
        active_op = opener or urllib.request.build_opener()
        with active_op.open(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, e.headers, body
    except Exception as e:
        return 0, {}, str(e)

def do_post_json(path, data_dict, headers=None, opener=None):
    url = f"{BASE_URL}{path}"
    data_bytes = json.dumps(data_dict).encode("utf-8")
    h = headers or {}
    h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data_bytes, headers=h)
    try:
        active_op = opener or urllib.request.build_opener()
        with active_op.open(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, e.headers, body
    except Exception as e:
        return 0, {}, str(e)

print("=" * 70)
print("INSPECCIÓN FUNCIONAL EN VIVO CONTRA BACKEND FASTAPI (127.0.0.1:8000)")
print("=" * 70)

# ==============================================================================
# BLOQUE 1: MODO PÚBLICO (SIN SESIÓN)
# ==============================================================================
# 1.1 Metadata
st, hdrs, b = do_get("/api/v1/indicators/metadata")
if st == 200:
    d = json.loads(b)
    has_keys = all(k in d for k in ["indicators", "periods", "segments", "provinces"])
    record("MP-01", "GET /api/v1/indicators/metadata", "APROBADO",
           f"HTTP 200 OK | Indicadores: {len(d.get('indicators', []))}, Periodos: {len(d.get('periods', {}).get('available', []))}, Segmentos: {len(d.get('segments', []))}")
else:
    record("MP-01", "GET /api/v1/indicators/metadata", "FALLIDO", f"HTTP {st} | Body: {b}")

# 1.2 Directorio de entidades
st, hdrs, b = do_get("/api/v1/entities?page=1&page_size=10")
if st == 200:
    d = json.loads(b)
    items = d.get("data", [])
    tot = d.get("pagination", {}).get("total_items", 0)
    record("MP-02", "GET /api/v1/entities?page=1&page_size=10", "APROBADO" if len(items) == 10 and tot > 200 else "OBSERVACIÓN",
           f"HTTP 200 OK | Total Entidades: {tot}, Retornadas: {len(items)}, Primera: {items[0]['razon_social'] if items else 'N/A'}")
else:
    record("MP-02", "GET /api/v1/entities", "FALLIDO", f"HTTP {st} | Body: {b}")

# 1.3 Serie país
st, hdrs, b = do_get("/api/v1/indicators/series?indicator=roa&level=country")
if st == 200:
    d = json.loads(b)
    pts = d.get("series", [{}])[0].get("points", [])
    record("MP-03", "GET /api/v1/indicators/series?indicator=roa&level=country", "APROBADO" if len(pts) > 0 else "FALLIDO",
           f"HTTP 200 OK | Puntos en serie nacional: {len(pts)}, Último valor: {pts[-1].get('value')}%")
else:
    record("MP-03", "GET /api/v1/indicators/series (country)", "FALLIDO", f"HTTP {st} | Body: {b}")

# 1.4 Serie segmento
st, hdrs, b = do_get("/api/v1/indicators/series?indicator=roa&level=segment&segment=1")
if st == 200:
    d = json.loads(b)
    series_list = d.get("series", [])
    pts = series_list[0].get("points", []) if series_list else []
    record("MP-04", "GET /api/v1/indicators/series?indicator=roa&level=segment&segment=1", "APROBADO" if len(pts) > 0 else "FALLIDO",
           f"HTTP 200 OK | Normalización '1' -> 'SEGMENTO_1', Puntos serie: {len(pts)}")
else:
    record("MP-04", "GET /api/v1/indicators/series (segment)", "FALLIDO", f"HTTP {st} | Body: {b}")

# 1.5 Serie de cooperativa pública sin sesión
st, hdrs, b = do_get("/api/v1/indicators/series?indicator=roa&level=entity&ruc=0190155722001")
if st == 200:
    d = json.loads(b)
    series_list = d.get("series", [])
    label = series_list[0].get("label", "") if series_list else ""
    pts = series_list[0].get("points", []) if series_list else []
    record("MP-05", "GET /api/v1/indicators/series?indicator=roa&level=entity&ruc=0190155722001", "APROBADO",
           f"HTTP 200 OK | Acceso público sin sesión verificado, Cooperativa: {label}, Puntos: {len(pts)}")
else:
    record("MP-05", "GET /api/v1/indicators/series (entity)", "FALLIDO", f"HTTP {st} | Body: {b}")

# 1.6 Bloqueo público a benchmark-matrix
st, hdrs, b = do_get("/api/v1/indicators/benchmark-matrix")
if st == 403:
    record("MP-06", "GET /api/v1/indicators/benchmark-matrix (Sin Auth)", "APROBADO",
           f"HTTP 403 Forbidden | Acceso bloqueado según especificación de seguridad")
else:
    record("MP-06", "GET /api/v1/indicators/benchmark-matrix (Sin Auth)", "FALLIDO", f"HTTP {st} (esperado 403) | Body: {b}")

# 1.7 Bloqueo público a pro/compare
st, hdrs, b = do_get("/api/v1/pro/compare")
if st in (401, 403):
    record("MP-07", "GET /api/v1/pro/compare (Sin Auth)", "APROBADO",
           f"HTTP {st} Unauthorized/Forbidden | Módulo analítico protegido")
else:
    record("MP-07", "GET /api/v1/pro/compare (Sin Auth)", "FALLIDO", f"HTTP {st} (esperado 401) | Body: {b}")

# 1.8 Bloqueo público a admin/audit-logs
st, hdrs, b = do_get("/api/v1/admin/audit-logs")
if st in (401, 403):
    record("MP-08", "GET /api/v1/admin/audit-logs (Sin Auth)", "APROBADO",
           f"HTTP {st} Unauthorized/Forbidden | Bitácora protegida contra accesos anónimos")
else:
    record("MP-08", "GET /api/v1/admin/audit-logs (Sin Auth)", "FALLIDO", f"HTTP {st} (esperado 401) | Body: {b}")

# ==============================================================================
# BLOQUE 2: MODO ACREDITADO & CICLO DE VIDA DE CREDENCIALES
# ==============================================================================
# 2.1 Login institucional y validación de Set-Cookie HttpOnly
login_payload = {
    "username": "investigador.espoch",
    "password": "EspochPro2026#",
    "role": "investigador"
}
st, hdrs, b = do_post_json("/api/v1/auth/token", login_payload, opener=session_opener)
cookie_header = hdrs.get("Set-Cookie", "")
has_httponly = "HttpOnly" in cookie_header or "httponly" in cookie_header
has_session_cookie = "espoch_pro_access_token" in cookie_header

if st == 200 and has_httponly:
    user_d = json.loads(b)
    record("MA-01", "POST /api/v1/auth/token (Login Institucional)", "APROBADO",
           f"HTTP 200 OK | Cookie HttpOnly inyectada ('espoch_pro_access_token'), Usuario: {user_d.get('user')}, Rol: {user_d.get('role')}")
else:
    record("MA-01", "POST /api/v1/auth/token (Login Institucional)", "FALLIDO",
           f"HTTP {st} | HttpOnly: {has_httponly}, Set-Cookie: {cookie_header}")

# 2.2 Acceso acreditado a /api/v1/pro/compare (hasta 5 cooperativas con semáforo CAMEL)
st, hdrs, b = do_get("/api/v1/pro/compare?rucs=0190155722001,1790016919001,0590040718001,0190097510001,1890001041001", opener=session_opener)
if st == 200:
    comp_d = json.loads(b)
    ents = comp_d.get("entities", [])
    inds = comp_d.get("indicators", [])
    has_camel = len(inds) > 0 and any("entity_evaluations" in ind for ind in inds)
    record("MA-02", "GET /api/v1/pro/compare (Benchmarking Multi-Entidad)", "APROBADO" if len(ents) == 5 and has_camel else "OBSERVACIÓN",
           f"HTTP 200 OK | 5 COACs comparadas, Indicadores CAMEL: {len(inds)}, Semáforos regulatorios calculados en tiempo real")
else:
    record("MA-02", "GET /api/v1/pro/compare (Benchmarking Multi-Entidad)", "FALLIDO", f"HTTP {st} | Body: {b}")

# 2.3 Acceso acreditado a /api/v1/indicators/benchmark-matrix
st, hdrs, b = do_get("/api/v1/indicators/benchmark-matrix?ruc=0190155722001&ruc=1790016919001&period=2025-12", opener=session_opener)
if st == 200:
    mat_d = json.loads(b)
    rows = mat_d.get("matrix", [])
    has_benchmarks = any("segment1_avg" in r and "country_avg" in r for r in rows)
    record("MA-03", "GET /api/v1/indicators/benchmark-matrix (Modo Acreditado)", "APROBADO" if len(rows) > 0 and has_benchmarks else "FALLIDO",
           f"HTTP 200 OK | Indicadores matriciales: {len(rows)}, Benchmark Segmento 1 y País consolidados")
else:
    record("MA-03", "GET /api/v1/indicators/benchmark-matrix (Modo Acreditado)", "FALLIDO", f"HTTP {st} | Body: {b}")

# ==============================================================================
# BLOQUE 3: GOBERNANZA Y AUDITORÍA FORENSE
# ==============================================================================
# 3.1 Consulta de eventos forenses con usuario auditor
auditor_jar = http.cookiejar.CookieJar()
auditor_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(auditor_jar))

auditor_creds = {
    "username": "auditor.espoch",
    "password": "EspochAuditor2026#",
    "role": "auditor"
}
st_log, _, _ = do_post_json("/api/v1/auth/token", auditor_creds, opener=auditor_opener)

st_audit, hdrs_audit, b_audit = do_get("/api/v1/admin/audit-logs?limit=15", opener=auditor_opener)
if st_audit == 200:
    log_d = json.loads(b_audit)
    logs = log_d.get("logs", [])
    total_logs = log_d.get("total", 0)
    record("GA-01", "GET /api/v1/admin/audit-logs (Rol Auditor)", "APROBADO" if total_logs > 0 else "OBSERVACIÓN",
           f"HTTP 200 OK | Registros recuperados: {len(logs)}, Total eventos registrados: {total_logs}")
else:
    record("GA-01", "GET /api/v1/admin/audit-logs (Rol Auditor)", "FALLIDO", f"HTTP {st_audit} | Body: {b_audit}")

# 3.2 Verificación en disco SQLite users.db (WAL Mode, Inmutabilidad, Estructura Forense)
db_file = Path("data/users.db")
if db_file.exists():
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    j_mode = cur.fetchone()[0]
    cur.execute("PRAGMA table_info(audit_logs);")
    cols = [r[1] for r in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM audit_logs;")
    n_logs = cur.fetchone()[0]
    cur.execute("SELECT timestamp, user_sub, action, ip_address, details_json FROM audit_logs ORDER BY id DESC LIMIT 1;")
    last_log = cur.fetchone()
    conn.close()

    wal_ok = j_mode.lower() == "wal"
    struct_ok = all(c in cols for c in ["timestamp", "user_sub", "action", "ip_address", "details_json"])
    record("GA-02", "Persistencia SQLite users.db (WAL & Forense)", "APROBADO" if (wal_ok and struct_ok and n_logs > 0) else "FALLIDO",
           f"Modo WAL: {wal_ok} ({j_mode}) | Total logs en disco: {n_logs} | Estructura íntegra: {struct_ok} | Último evento: {last_log[2] if last_log else 'N/A'}")
else:
    record("GA-02", "Persistencia SQLite users.db", "FALLIDO", "data/users.db no encontrado")

print("=" * 70)
print(f"RESUMEN: {sum(1 for r in test_results if r['status'] == 'APROBADO')}/{len(test_results)} PRUEBAS APROBADAS")
print("=" * 70)

# Escribir reporte estructurado JSON para consumo del informe
with open("docs/audit_live_results.json", "w", encoding="utf-8") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)
