"""
policy_manager.py
---------------------------------------------------
Analiza el historial de tareas (Elastic + Cognition)
y genera "políticas" de mejora para el Orchestrator.
---------------------------------------------------
"""

import aiohttp
import os
import json
from state_producer import send_state_update

ELASTIC_URL = os.getenv(
    "ELASTIC_URL", "http://elasticsearch:9200/state_manager_v1/_search"
)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama-service:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


# ============================================================
# 🔸 Recuperar historial de tareas recientes desde Elastic
# ============================================================
async def fetch_recent_tasks(n: int = 10) -> list[dict]:
    """
    Recupera los últimos N eventos de tipo 'task_complete' desde Elastic.
    """
    query = {
        "size": n,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": ["task_id", "stage", "message", "@timestamp"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(ELASTIC_URL, json=query, timeout=30) as r:
            data = await r.json()
            hits = data.get("hits", {}).get("hits", [])
            return [hit["_source"] for hit in hits]


# ============================================================
# 🔹 Enviar petición a Llama 3.1 (Ollama) y leer stream NDJSON
# ============================================================
async def ask_llama_for_policy(history: list[dict]) -> str:
    """
    Envía a Llama 3.1 una petición de síntesis de políticas meta‑cognitivas.
    Lee NDJSON streaming y devuelve el texto limpio.
    """
    text_hist = json.dumps(history, ensure_ascii=False, indent=2)
    prompt = f"""
Eres un agente cognitivo que debe revisar su comportamiento pasado.

A continuación tienes el historial reciente de tareas completadas con su resultado:

{text_hist}

Analiza:
1. ¿Qué patrones de éxito o fallo se aprecian?
2. ¿Qué decisiones debería repetir o evitar el agente?
3. Propón una "política de mejora" corta (máx 5 líneas).

Devuelve texto plano.
"""

    payload = {"model": MODEL, "prompt": prompt, "stream": True}
    full_text = ""

    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload, timeout=120) as resp:
            async for raw_line in resp.content:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Solo concatenamos el campo "response"
                    if "response" in data:
                        full_text += data["response"]
                except json.JSONDecodeError:
                    # línea posiblemente incompleta → ignorar
                    continue

    return full_text.strip()


# ============================================================
# 🧠 Proceso completo de meta-reflexión
# ============================================================
async def run_meta_reflection():
    """
    Ejecuta el ciclo meta‑reflexivo:
      - extrae historial reciente desde Elastic
      - analiza con Llama 3.1 por stream NDJSON
      - almacena insight final en Kafka (stage: meta_reflection)
      - ejecuta feedback adaptativo (ajuste de pesos)
    """
    try:
        history = await fetch_recent_tasks(8)
        if not history:
            raise ValueError("No se encontraron eventos recientes en Elastic")

        reflection = await ask_llama_for_policy(history)

        send_state_update("policy", "meta_reflection", reflection or "(vacío)")
        print("🧩 Meta‑reflexión generada:")
        print(reflection[:800] if reflection else "(sin texto)")

        # ============================================================
        # 🔁  Fase 10 – Policy Feedback Loop (auto‑aprendizaje)
        # ============================================================
        try:
            from policy_feedback import run_policy_feedback
            print("🧠 Ejecutando feedback cognitivo automático...")
            run_policy_feedback()
            print("✅ Feedback Loop completado (ajuste de pesos actualizado).")
        except Exception as fb_err:
            print(f"⚠️ Error en feedback cognitivo: {type(fb_err).__name__}: {fb_err}")

        return reflection

    except Exception as e:
        send_state_update("policy", "meta_reflection_error", str(e))
        print(f"❌ Error en meta‑reflexión: {type(e).__name__}: {e}")
        return ""
