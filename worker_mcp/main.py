"""
main.py
Servicio FastAPI del Worker_MCP.
Recibe tareas desde el Orchestrator por HTTP.
"""

from json_logger import log_event
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from llm_worker import generate_code_response
from state_producer import send_state_update

app = FastAPI(title="Worker_MCP", version="1.0")

# ---------- Modelos de datos ----------
class ActRequest(BaseModel):
    task_id: str
    task: str
    context: dict | None = None


class ActResponse(BaseModel):
    task_id: str
    result: str
    context: dict


# ---------- Funciones utilitarias ----------
def log_ctx(task_id: str, action: str, info: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WORKER_CTX] {timestamp} | Task={task_id} | Action={action} | {info}")


# ---------- Endpoints ----------
@app.get("/status")
def get_status():
    return {"status": "ok", "model": "CodeLlama 7B (Ollama local)"}


@app.post("/act", response_model=ActResponse)
def act_on_task(request: ActRequest):
    log_ctx(request.task_id, "received", request.task[:80])
    log_event("worker_mcp", "INFO", "task_received", f"Received task {request.task_id}", task_id=request.task_id)
    send_state_update(request.task_id, "task_received", "Worker MCP recibió la tarea")

    result = generate_code_response(request.task)

    # Actualiza el contexto (futuro: persistencia en ChromaDB)
    context_out = request.context or {}
    context_out.update({
        "worker_action": "code_generation",
        "worker_status": "done",
        "timestamp": datetime.now().isoformat(),
    })

    log_ctx(request.task_id, "processed", "Task completed successfully.")
    log_event("worker_mcp", "INFO", "task_completed", f"Completed {request.task_id}", task_id=request.task_id)
    send_state_update(request.task_id, "task_completed", "Worker MCP completó la tarea")

    return ActResponse(task_id=request.task_id, result=result, context=context_out)
