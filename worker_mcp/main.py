"""
main.py
Servicio FastAPI del Worker_MCP.
------------------------------------------------------------
Recibe tareas desde el Orchestrator por HTTP.
Antes de generar o modificar código:
  🔹 valida el archivo con Context7 MCP Server
  🔹 genera código con CodeLlama (Ollama)
  🔹 publica estado en Kafka (state_update)
------------------------------------------------------------
"""

from json_logger import log_event
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from llm_worker import generate_code_response
from state_producer import send_state_update
from context7_client import validate_file   # 🆕 añadido

import asyncio

app = FastAPI(title="Worker_MCP", version="1.1")

# ---------- Modelos de datos ----------
class ActRequest(BaseModel):
    task_id: str
    task: str
    context: dict | None = None


class ActResponse(BaseModel):
    task_id: str
    result: str
    context: dict


# ---------- Función utilitaria ----------
def log_ctx(task_id: str, action: str, info: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WORKER_CTX] {timestamp} | Task={task_id} | Action={action} | {info}")


# ---------- Endpoints ----------
@app.get("/status")
def get_status():
    return {"status": "ok", "model": "CodeLlama 7B (Ollama local)"}


@app.post("/act", response_model=ActResponse)
def act_on_task(request: ActRequest):
    """
    Flujo completo de tarea del Worker:
      1️⃣ Recibe tarea del Orchestrator
      2️⃣ Valida el archivo con Context7
      3️⃣ Genera código (CodeLlama)
      4️⃣ Devuelve resultado y eventos Kafka
    """
    task_id = request.task_id
    prompt = request.task

    # 🧠 1️⃣ Recepción
    log_ctx(task_id, "received", prompt[:80])
    log_event("worker_mcp", "INFO", "task_received", f"Received task {task_id}", task_id=task_id)
    send_state_update(task_id, "task_received", "Worker MCP recibió la tarea")

    # ─────────────────────────────────────────────
    # 🧩 2️⃣ Validar archivo con Context7
    # ─────────────────────────────────────────────
    target_file = "workspace/output.py"  # ejemplo base; puedes derivarlo del prompt
    try:
        result_validation = asyncio.run(validate_file(task_id, target_file))
    except RuntimeError:
        # para compatibilidad con event loops existentes (FastAPI)
        result_validation = asyncio.get_event_loop().run_until_complete(validate_file(task_id, target_file))

    if result_validation.get("status") == "error":
        reason = result_validation.get("error", "(unknown)")
        log_ctx(task_id, "context7_error", reason)
        log_event("worker_mcp", "ERROR", "context7_error", reason, task_id=task_id)
        send_state_update(task_id, "context7_refused", f"Archivo no válido: {reason}")
        raise HTTPException(status_code=500, detail=f"Context7 validation failed: {reason}")

    send_state_update(task_id, "context7_validated", f"Archivo {target_file} verificado por Context7")
    log_ctx(task_id, "context7_validated", f"File {target_file} OK")

    # ─────────────────────────────────────────────
    # 🧠 3️⃣ Generar código con CodeLlama
    # ─────────────────────────────────────────────
    result = generate_code_response(prompt)

    # ─────────────────────────────────────────────
    # 🗂️ 4️⃣ Actualizar contexto y registrar eventos
    # ─────────────────────────────────────────────
    context_out = request.context or {}
    context_out.update({
        "worker_action": "code_generation",
        "worker_status": "done",
        "timestamp": datetime.now().isoformat(),
        "file": target_file,
    })

    log_ctx(task_id, "processed", "Task completed successfully.")
    log_event("worker_mcp", "INFO", "task_completed", f"Completed {task_id}", task_id=task_id)
    send_state_update(task_id, "task_completed", f"Worker MCP completó la tarea en {target_file}")

    return ActResponse(task_id=task_id, result=result, context=context_out)

@app.get("/health")
def health_check():
    return JSONResponse(content={"worker_mcp": "ok"}, status_code=200)
