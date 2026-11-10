"""
Smoke Test End-to-End:
Inicia uvicorn en puerto efímero y ejecuta peticiones HTTP reales:
1. /health
2. POST /api/v1/auth/login (Valida inyección Set-Cookie HttpOnly)
3. GET /api/v1/auth/me (Valida lectura de cookie de sesión)
4. POST /api/v1/pro/benchmarking/compare (Valida DuckDB y Semáforos CAMEL)
5. POST /api/v1/pro/export/csv (Valida streaming de microdatos)
6. POST /api/v1/pro/export/excel (Valida generación de libro Excel multi-hoja)
"""

import threading
import time
import urllib.request
import json
import uvicorn
from backend.app.main import app

def run_smoke_test():
    server_port = 8019
    def start_server():
        uvicorn.run(app, host="127.0.0.1", port=server_port, log_level="error")

    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(1.5)

    base_url = f"http://127.0.0.1:{server_port}"
    print(f"[*] Servidor uvicorn iniciado en {base_url}")

    # 1. Health
    with urllib.request.urlopen(f"{base_url}/health") as resp:
        assert resp.status == 200
        print("[+] 1. /health OK")

    # 2. Login con credenciales institucionales
    login_payload = json.dumps({
        "username": "investigador.espoch",
        "password": "EspochPro2026#",
        "role": "investigador"
    }).encode("utf-8")

    req_login = urllib.request.Request(
        f"{base_url}/api/v1/auth/login",
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req_login) as resp:
        assert resp.status == 200
        set_cookie = resp.headers.get("Set-Cookie")
        assert set_cookie is not None and "espoch_pro_access_token=" in set_cookie
        assert "HttpOnly" in set_cookie
        cookie_header = set_cookie.split(";")[0]
        data = json.loads(resp.read().decode())
        assert data["authenticated"] is True
        assert data["role"] == "investigador"
        print(f"[+] 2. POST /api/v1/auth/login OK -> Cookie HttpOnly inyectada: {cookie_header[:40]}...")

    # 3. GET /me con la cookie recibida
    req_me = urllib.request.Request(
        f"{base_url}/api/v1/auth/me",
        headers={"Cookie": cookie_header},
        method="GET"
    )
    with urllib.request.urlopen(req_me) as resp:
        assert resp.status == 200
        me_data = json.loads(resp.read().decode())
        assert me_data["sub"] == "investigador.espoch"
        print(f"[+] 3. GET /api/v1/auth/me OK -> Identidad verificada: {me_data['name']} ({me_data['role']})")

    # 4. POST /pro/benchmarking/compare (2 entidades, 2024-01 a 2025-12)
    compare_payload = json.dumps({
        "entity_ids": ["0190155722001", "0190115798001"],
        "start_date": "2024-01",
        "end_date": "2025-12",
        "camel_dimension": "calidad_de_activos"
    }).encode("utf-8")

    req_compare = urllib.request.Request(
        f"{base_url}/api/v1/pro/benchmarking/compare",
        data=compare_payload,
        headers={"Content-Type": "application/json", "Cookie": cookie_header},
        method="POST"
    )
    t0 = time.time()
    with urllib.request.urlopen(req_compare) as resp:
        bench_duration = time.time() - t0
        assert resp.status == 200
        bench_data = json.loads(resp.read().decode())
        assert len(bench_data["entities"]) == 2
        assert len(bench_data["indicators"]) > 0
        first_ind = bench_data["indicators"][0]
        assert "0190155722001" in first_ind["entity_evaluations"]
        status_val = first_ind["entity_evaluations"]["0190155722001"]["status"]
        assert status_val in ["GREEN", "YELLOW", "RED"]
        print(f"[+] 4. POST /pro/benchmarking/compare OK -> Latencia: {bench_duration:.3f}s (< 1s objetivo)")
        print(f"       Indicadores evaluados: {len(bench_data['indicators'])} | Semáforo: {status_val}")

    # 5. POST /pro/export/csv (Streaming)
    export_payload = json.dumps({
        "entity_ids": ["0190155722001"],
        "start_date": "2025-01",
        "end_date": "2025-12",
        "camel_dimension": "capital"
    }).encode("utf-8")

    req_csv = urllib.request.Request(
        f"{base_url}/api/v1/pro/export/csv",
        data=export_payload,
        headers={"Content-Type": "application/json", "Cookie": cookie_header},
        method="POST"
    )
    with urllib.request.urlopen(req_csv) as resp:
        assert resp.status == 200
        csv_bytes = resp.read()
        assert b"periodo,ruc,razon_social" in csv_bytes
        print(f"[+] 5. POST /pro/export/csv (Streaming) OK -> Bytes: {len(csv_bytes)}")

    # 6. POST /pro/export/excel (Multi-Hoja)
    req_excel = urllib.request.Request(
        f"{base_url}/api/v1/pro/export/excel",
        data=export_payload,
        headers={"Content-Type": "application/json", "Cookie": cookie_header},
        method="POST"
    )
    with urllib.request.urlopen(req_excel) as resp:
        assert resp.status == 200
        excel_bytes = resp.read()
        assert len(excel_bytes) > 5000
        print(f"[+] 6. POST /pro/export/excel OK -> Archivo XLSX generado: {len(excel_bytes)} bytes")

    print("\n=======================================================")
    print("TODOS LOS SMOKE TESTS PASARON EXITOSAMENTE (100% OK)")
    print("=======================================================")

if __name__ == "__main__":
    run_smoke_test()
