"""
Orchestrator - RAG Megalab
------------------------------------------------------------
Coordina todo el flujo cognitivo:
  ▪ Recibe prompts y gestiona proyectos activos.
  ▪ Razonamiento adaptativo (Llama 3.1 + Policy Tuner).
  ▪ Aplica estrategias dinámicas (Strategy Manager).
  ▪ Delegación segura al Worker MCP.
  ▪ Persistencia en Chroma + Elastic.
  ▪ Supervisor + Meta‑Reflexión (+ Feedback Loop).
------------------------------------------------------------
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import threading, asyncio, uuid, traceback

from llm_orch import build_ollama_chain
from worker_client import send_task_to_worker
from context_manager import store_context_entry
from json_logger import log_event
from state_producer import send_state_update

# 🧠  Módulos cognitivos
from reasoning_supervisor import run_supervisor
from policy_manager import run_meta_reflection
from policy_adapter import load_adaptive_context

# 🪄  Nuevos módulos  (FASE 11 + 11‑BIS)
from strategy_manager import load_policy_weights, select_strategies, apply_strategy
from project_manager.manifest import create_manifest, append_prompt, close_project

# 🩺 Health System (FASE 14‑A)
from health_manager import start_health_monitor

# 🩺 Health System (FASE 14‑B)
from policy_feedback import listen_health_feedback

from healing_manager import listen_state_for_errors

app = FastAPI(title="Orchestrator - RAG Megalab")
chain = build_ollama_chain()


# ---------------------------------------------------------------------
class PromptRequest(BaseModel):
    prompt: str
# ---------------------------------------------------------------------


@app.post("/prompt")
def handle_prompt(body: PromptRequest):
    """
    Flujo principal de ejecución:
      1️⃣  Recibe prompt y mantiene contexto de proyecto.
      2️⃣  Carga políticas adaptativas y estrategias dinámicas.
      3️⃣  Ejecuta Llama 3.1 (adaptativo) y delega al Worker MCP.
      4️⃣  Persiste contexto + publica eventos.
      5️⃣  Ejecuta Supervisor + Meta‑Reflexión (+ Feedback).
    """
    task_id = f"TASK-{uuid.uuid4().hex[:8]}"

    try:
        # ----------------------------------------------------- 1️⃣ Prompt recibido
        log_event("orchestrator","INFO","prompt_received",
                  f"Nuevo prompt recibido: {body.prompt[:60]}...", task_id=task_id)
        send_state_update(task_id,"prompt_received",body.prompt[:80])

        store_context_entry(
            text=body.prompt,
            metadata={"role": "user","stage": "prompt_received","task_id": task_id},
        )

        # 📁 Determinar o crear proyecto activo
        if not hasattr(app.state, "active_project_id"):
            app.state.active_project_id = create_manifest(body.prompt)
        else:
            append_prompt(app.state.active_project_id, body.prompt)
        project_id = app.state.active_project_id

        # ----------------------------------------------------- 2️⃣ Estrategias dinámicas
        weights = load_policy_weights()
        plan = select_strategies(weights)
        apply_strategy(plan, task_id)

        # ----------------------------------------------------- 3️⃣ Razonamiento Llama 3.1 adaptativo
        log_event("orchestrator","INFO","llama_invoke",
                  "Ejecutando cadena Llama 3.1 adaptativo", task_id=task_id)

        adaptive_prefix = load_adaptive_context()
        full_prompt = f"{adaptive_prefix}\n\n{body.prompt}" if adaptive_prefix else body.prompt
        result = chain.invoke({"prompt": full_prompt})

        response_text = (
            result.get("text")
            if isinstance(result, dict)
            else getattr(result, "content", str(result))
        )

        send_state_update(task_id,"llama_result_ok",
                          f"Respuesta adaptativa de {len(response_text)} caracteres")

        # ----------------------------------------------------- 4️⃣  Worker MCP
        context = {"origin": "orchestrator","stage": "delegation"}
        worker_resp = send_task_to_worker(task_id, body.prompt, context)
        send_state_update(task_id,"worker_dispatched","Tarea enviada al Worker MCP")

        # ----------------------------------------------------- 5️⃣  Persistencia contexto
        combined_text = (f"ORCHESTRATOR:\n{response_text}\n\n"
                         f"WORKER:\n{worker_resp.get('result','(sin resultado)')}")
        store_context_entry(
            text=combined_text,
            metadata={"role": "system","stage": "worker_response","task_id": task_id},
        )
        send_state_update(task_id,"context_persisted","Contexto almacenado en Chroma")

        # ----------------------------------------------------- 6️⃣  Completar tarea principal
        send_state_update(task_id,"task_complete","Ejecución finalizada correctamente")

        # ----------------------------------------------------- 7️⃣  Supervisor + Meta‑Reflexión
        def _run_async_tasks():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run_supervisor(task_id, body.prompt))
                loop.run_until_complete(asyncio.sleep(3))
                loop.run_until_complete(run_meta_reflection())
            except Exception as e:
                send_state_update(task_id,"async_task_error",str(e))
                print(f"❌ Error en hilo async ({type(e).__name__}): {e}")
            finally:
                loop.close()

        threading.Thread(target=_run_async_tasks, daemon=True).start()
        send_state_update(task_id,"supervisor_invoked",
                          "Supervisor + Meta‑Reflexión en ejecución")

        # ----------------------------------------------------- 8️⃣  Retornar respuesta al Gateway
        return {
            "task_id": task_id,
            "project_id": project_id,
            "prompt": body.prompt,
            "adaptive_prefix_applied": bool(adaptive_prefix.strip()),
            "orchestrator_summary": response_text,
            "worker_result": worker_resp.get("result", "(no result)"),
        }

    except Exception as e:
        traceback.print_exc()
        send_state_update(task_id,"execution_error",f"{type(e).__name__}: {e}")
        store_context_entry(
            text=f"Error en ejecución: {type(e).__name__}: {e}",
            metadata={"role": "system","stage": "error","task_id": task_id},
        )
        return {"task_id": task_id, "error": f"{type(e).__name__}: {e}"}
# ---------------------------------------------------------------------


@app.get("/status")
def status():
    """Healthcheck básico."""
    return {"status": "orchestrator_ready"}


@app.get("/health")
def health_check():
    """Endpoint de salud para observabilidad."""
    return JSONResponse(content={"orchestrator": "ok"}, status_code=200)

@app.on_event("startup")
def startup_event():
    """Arranque del Health Monitor y Feedback Técnico."""
    import threading
    threading.Thread(target=start_health_monitor, daemon=True).start()
    threading.Thread(target=listen_health_feedback, daemon=True).start()
    print("🩺 Health Manager y Feedback Técnico iniciados (thread daemon).")

@app.on_event("startup")
def startup_event():
    import threading
    threading.Thread(target=start_health_monitor, daemon=True).start()
    threading.Thread(target=listen_health_feedback, daemon=True).start()
    threading.Thread(target=listen_state_for_errors, daemon=True).start()
    print("🩺 Health Manager, Feedback Técnico y Healing Listener iniciados (thread daemon).")
