"""
Orchestrator - RAG Megalab
------------------------------------------------------------
Recibe un prompt del usuario, coordina ejecución de Llama 3.1
y delega tareas al Worker MCP.

🔹 Emite logs estructurados en Kafka (topic state_update)
🔹 Persiste contexto en Chroma
🔹 Ejecuta Supervisor Cognitivo (FASE 8.2)
🔹 Ejecuta Meta‑Reflexión (FASE 8.3)
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

# 🧠 Módulos cognitivos
from reasoning_supervisor import run_supervisor
from policy_manager import run_meta_reflection
import threading
import asyncio
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
      2️⃣ Ejecuta cadena de razonamiento (Llama 3.1).
      3️⃣ Delegación al Worker MCP.
      4️⃣ Persistencia contextual + publicación de estado.
      5️⃣ Ejecuta Supervisor Cognitivo (8.2).
      6️⃣ Dispara ciclo Meta‑Reflexivo (8.3).
    """
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"

    try:
        # ----------------- 1️⃣ Prompt recibido -----------------
        log_event(
            "orchestrator",
            "INFO",
            "prompt_received",
            f"Nuevo prompt recibido: {body.prompt[:60]}...",
            task_id=task_id,
        )
        send_state_update(task_id, "prompt_received", f"{body.prompt[:80]}")

        store_context_entry(
            text=body.prompt,
            metadata={"role": "user", "stage": "prompt_received", "task_id": task_id},
        )

        # ---------------- 2️⃣ Razonamiento Llama 3.1 ------------
        log_event("orchestrator", "INFO", "llama_invoke", "Ejecutando cadena Llama3.1", task_id=task_id)
        result = chain.invoke({"prompt": body.prompt})
        response_text = (
            result.get("text")
            if isinstance(result, dict)
            else getattr(result, "content", str(result))
        )

        send_state_update(task_id, "llama_result_ok", f"Respuesta de {len(response_text)} caracteres")

        # ----------------- 3️⃣ Worker MCP -----------------
        context = {"origin": "orchestrator", "stage": "delegation"}
        worker_resp = send_task_to_worker(task_id, body.prompt, context)
        send_state_update(task_id, "worker_dispatched", "Tarea enviada al Worker MCP")

        # ---------------- 4️⃣ Persistencia contexto ------------
        combined_text = (
            f"ORCHESTRATOR:\n{response_text}\n\n"
            f"WORKER:\n{worker_resp.get('result', '(sin resultado)')}"
        )
        store_context_entry(
            text=combined_text,
            metadata={"role": "system", "stage": "worker_response", "task_id": task_id},
        )
        send_state_update(task_id, "context_persisted", "Contexto almacenado en Chroma")

        # ---------------- 5️⃣ Completar tarea principal ----------
        send_state_update(task_id, "task_complete", "Ejecución finalizada correctamente")

        # ---------------- 6️⃣ Supervisor + Meta-Reflexión --------
        def _run_async_tasks():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # Supervisor y reflexión se lanzan secuencialmente
                loop.run_until_complete(run_supervisor(task_id, body.prompt))
                loop.run_until_complete(asyncio.sleep(3))
                loop.run_until_complete(run_meta_reflection())
            except Exception as e:
                send_state_update(task_id, "async_task_error", str(e))
                print(f"❌ Error en hilo async: {type(e).__name__}: {e}")
            finally:
                loop.close()

        threading.Thread(target=_run_async_tasks, daemon=True).start()
        send_state_update(task_id, "supervisor_invoked", "Supervisor + Meta‑Reflexión en ejecución")

        # ---------------- 7️⃣ Respuesta API Gateway --------------
        return {
            "task_id": task_id,
            "prompt": body.prompt,
            "orchestrator_summary": response_text,
            "worker_result": worker_resp.get("result", "(no result)"),
        }

    except Exception as e:
        traceback.print_exc()
        send_state_update(task_id, "execution_error", f"{type(e).__name__}: {e}")
        store_context_entry(
            text=f"Error en ejecución: {type(e).__name__}: {e}",
            metadata={"role": "system", "stage": "error", "task_id": task_id},
        )
        return {"task_id": task_id, "error": f"{type(e).__name__}: {e}"}


@app.get("/status")
def status():
    """Healthcheck básico."""
    return {"status": "orchestrator_ready"}


@app.get("/health")
def health_check():
    """Endpoint de salud para observabilidad."""
    return JSONResponse(content={"orchestrator": "ok"}, status_code=200)
