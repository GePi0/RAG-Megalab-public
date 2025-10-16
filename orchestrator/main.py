"""
Orchestrator - RAG Megalab
------------------------------------------------------------
Recibe un prompt del usuario, coordina ejecución de la cadena
Llama 3.1 y delega tareas al Worker MCP.

🔹 Emite logs estructurados en `rag_logs_v2`
🔹 Publica eventos cognitivos al topic `state_update`
------------------------------------------------------------
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from llm_orch import build_ollama_chain
from worker_client import send_task_to_worker
from context_manager import store_context_entry
from json_logger import log_event
from state_producer import send_state_update

import uuid
import traceback


app = FastAPI(title="Orchestrator - RAG Megalab")
chain = build_ollama_chain()


# ------------------- MODELOS -------------------
class PromptRequest(BaseModel):
    prompt: str


# ------------------- ENDPOINTS -------------------
@app.post("/prompt")
def handle_prompt(body: PromptRequest):
    """
    Flujo principal de ejecución:
      1️⃣ Recibe prompt del usuario.
      2️⃣ Ejecuta la cadena de razonamiento (Llama 3.1).
      3️⃣ Delegación de tarea al Worker MCP.
      4️⃣ Persistencia contextual + publicación de estado.
    """
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"

    try:
        # 🧠 1️⃣ Prompt recibido
        log_event(
            "orchestrator",
            "INFO",
            "prompt_received",
            f"Nuevo prompt recibido: {body.prompt[:60]}...",
            task_id=task_id,
        )
        send_state_update(task_id, "prompt_received", f"Prompt recibido: {body.prompt[:60]}")

        # Persistir en memoria vectorial
        store_context_entry(
            text=body.prompt,
            metadata={"role": "user", "action": "prompt_received", "task_id": task_id},
        )

        # 🦙 2️⃣ Ejecución con Llama 3.1
        log_event("orchestrator", "INFO", "llama_invoke", "Ejecutando cadena Llama3.1", task_id=task_id)

        result = chain.invoke({"prompt": body.prompt})

        if isinstance(result, dict):
            response_text = result.get("text") or result.get("output_text")
        else:
            response_text = getattr(result, "content", str(result))

        log_event(
            "orchestrator",
            "INFO",
            "llama_result_ok",
            f"Respuesta intermedia OK ({len(response_text)} chars)",
            task_id=task_id,
        )
        send_state_update(task_id, "llama_result_ok", "Llama 3.1 generó una respuesta intermedia")

        # 🧱 3️⃣ Delegar tarea al Worker MCP
        context = {"origin": "orchestrator", "stage": "delegation"}
        worker_resp = send_task_to_worker(task_id, body.prompt, context)
        log_event(
            "orchestrator",
            "INFO",
            "worker_dispatched",
            "Tarea delegada al Worker MCP",
            task_id=task_id,
        )
        send_state_update(task_id, "worker_dispatched", "Tarea delegada al Worker MCP")

        # 🧠 4️⃣ Consolidar y almacenar el contexto completo
        combined_text = (
            f"ORCHESTRATOR:\n{response_text}\n\n"
            f"WORKER:\n{worker_resp.get('result', '(no result)')}"
        )
        store_context_entry(
            text=combined_text,
            metadata={"role": "system", "action": "worker_response", "task_id": task_id},
        )
        log_event(
            "orchestrator",
            "INFO",
            "context_persisted",
            "Prompt + respuesta almacenados en ChromaDB",
            task_id=task_id,
        )
        send_state_update(task_id, "context_persisted", "Prompt + respuesta almacenados en memoria")

        # 📦 5️⃣ Finalizar la tarea
        log_event("orchestrator", "INFO", "task_complete", "Tarea completada sin errores", task_id=task_id)
        send_state_update(task_id, "task_complete", "Tarea completada satisfactoriamente")

        # Respuesta al API Gateway
        return {
            "task_id": task_id,
            "prompt": body.prompt,
            "orchestrator_response": response_text,
            "worker_result": worker_resp.get("result", "(no result)"),
            "context": worker_resp.get("context", {}),
        }

    except Exception as e:
        traceback.print_exc()
        log_event("orchestrator", "ERROR", "execution_error", f"Error inesperado: {e}", task_id=task_id)
        send_state_update(task_id, "execution_error", f"Error inesperado durante ejecución: {e}")
        store_context_entry(
            text=f"Error en ejecución: {e}",
            metadata={"role": "system", "action": "error", "task_id": task_id},
        )
        return {"task_id": task_id, "error": str(e)}


@app.get("/status")
def status():
    """Verifica que el servicio está listo."""
    return {"status": "orchestrator_ready"}


@app.get("/health")
def health_check():
    return JSONResponse(content={"orchestrator": "ok"}, status_code=200)
