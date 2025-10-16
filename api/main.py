"""
API Gateway – RAG Megalab
--------------------------
Puerta de entrada unificada: recibe requests del usuario
y los reenvía al Orchestrator (servicio 8001).
"""

from json_logger import log_event
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import httpx, os, time

app = FastAPI(title="RAG Megalab API Gateway", version="6.5")

# =========================================================
# Configuración
# =========================================================
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8001")

# =========================================================
# Endpoints
# =========================================================
@app.get("/health")
async def health_check():
    """Comprueba disponibilidad del Gateway y del Orchestrator"""
    t0 = time.time()
    orch_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/health")
            orch_status = "ok" if r.status_code == 200 else f"code {r.status_code}"
    except Exception as e:
        orch_status = f"unreachable ({e})"
    latency = round((time.time() - t0) * 1000, 2)
    log_event("api", "INFO", "health_check", "Gateway health endpoint called", latency_ms=latency)
    return {"gateway": "ok", "orchestrator": orch_status, "latency_ms": latency}


@app.post("/prompt")
async def forward_prompt(request: Request):
    """
    Reenvía la solicitud JSON al Orchestrator y devuelve su respuesta.
    """
    data = await request.json()   # 🔹 Lee el cuerpo solo una vez

    log_event(
        "api",
        "INFO",
        "prompt_forwarded",
        "Forwarding user prompt to orchestrator",
        prompt=data.get("prompt", "(no prompt)")
    )

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(f"{ORCHESTRATOR_URL}/prompt", json=data)

        elapsed = round((time.time() - t0) * 1000, 2)
        response_data = r.json()

        return JSONResponse(
            content={
                "gateway_latency_ms": elapsed,
                "orchestrator_response": response_data,
            },
            status_code=r.status_code,
        )

    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
