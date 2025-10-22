# orchestrator/health_manager.py
"""
health_manager.py – Monitor y autocuración operacional (FASE 14‑A)
------------------------------------------------------------------
Verifica endpoints /health de servicios clave e integra meta‑reflexión.
Si detecta fallo crítico, llama AutoRepair y registra incidente.
------------------------------------------------------------------
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from auto_repair import handle_restart
from incident_logger import log_incident
from state_producer import send_state_update
from pathlib import Path

INTERVAL = int(os.getenv("HEALTH_INTERVAL_SEC", 20))
RETRY_LIMIT = int(os.getenv("RETRY_LIMIT", 3))

SERVICES = {
    "api": "http://api:8000/health",
    "context_service": "http://context_service:8002/health",
    "worker_mcp": "http://worker_mcp:8003/health",
    "orchestrator": "http://orchestrator:8001/health",
}

REFLECTION_FILE = Path("/storage/logs/orchestrator/latest_reflection.json")

async def check_service(session, name, url):
    try:
        async with session.get(url, timeout=5) as r:
            ok = r.status == 200
            return {"service": name, "ok": ok, "status": r.status}
    except Exception as e:
        return {"service": name, "ok": False, "error": str(e)}

async def monitor_services():
    print("🩺 [health_manager] Monitor de salud iniciado.")
    consecutive_failures = {s: 0 for s in SERVICES}

    while True:
        async with aiohttp.ClientSession() as session:
            for name, url in SERVICES.items():
                result = await check_service(session, name, url)

                # -------- OK
                if result["ok"]:
                    consecutive_failures[name] = 0
                    log_incident(name, "INFO", "health_ok", f"Servicio {name} responde 200.")
                    send_state_update("HEALTH", f"{name}_ok", "Servicio operativo")
                    continue

                # -------- FAIL
                consecutive_failures[name] += 1
                log_incident(name, "WARNING", "health_fail",
                             f"Fallo detectado ({result.get('error','code')})",
                             attempt=consecutive_failures[name])

                if consecutive_failures[name] >= RETRY_LIMIT:
                    log_incident(name, "ERROR", "health_critical",
                                 f"Reintentos agotados. Reinicio de {name}...")
                    res = handle_restart(name)
                    send_state_update("HEALTH", f"{name}_restart", json.dumps(res))
                    consecutive_failures[name] = 0  # reset tras acción

        # ---- Integra meta‑reflexión si existe
        if REFLECTION_FILE.exists():
            try:
                text = REFLECTION_FILE.read_text(encoding="utf‑8")
                if "Error code" in text or "timeout" in text.lower():
                    log_incident("meta_reflection", "INFO", "analysis_hint",
                                 "Meta‑reflexión detectó posible fallo de comunicación",
                                 hint_source="meta_reflection")
            except Exception:
                pass

        await asyncio.sleep(INTERVAL)

def start_health_monitor():
    """Lanzar en thread independiente desde main.py"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor_services())
