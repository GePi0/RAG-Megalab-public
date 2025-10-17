# reasoning_supervisor.py  ────────────────────────────
import aiohttp
import asyncio
import datetime
import os
import json
from state_producer import send_state_update
from uuid import uuid4

# ── URLs internas de los microservicios ─────────────────────────
STATE_MANAGER_URL = os.getenv(
    "STATE_MANAGER_URL", "http://state_manager:8010/memory/query"
)
# Context7 escucha internamente en 8080
CONTEXT7_URL = os.getenv("CONTEXT7_URL", "http://context7:8080/mcp")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama-service:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

# ─────────────────────────────────────────────
# Consulta de memoria cognitiva
# ─────────────────────────────────────────────
async def query_memory(text_query: str, k: int = 5):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            STATE_MANAGER_URL, json={"query": text_query, "k": k}, timeout=60
        ) as resp:
            return await resp.json()

# ─────────────────────────────────────────────
# Consulta del estado del proyecto a Context7
# ─────────────────────────────────────────────
async def query_context7(task_id: str, project_path: str = "/workspace"):
    """Obtiene resumen del entorno de archivos desde Context7 MCP (modo JSON-RPC)."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "analyze",
            "params": {"path": project_path},
            "id": 1,
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CONTEXT7_URL}",
                json=payload,
                headers=headers,
                timeout=30,
            ) as resp:
                # usamos texto completo porque Context7 devuelve NDJSON
                text = await resp.text()
                send_state_update(
                    task_id,
                    "context7_checked",
                    f"Context7 analizó el entorno {project_path}",
                )
                return {"raw_response": text}
    except Exception as e:
        send_state_update(
            task_id,
            "context7_error",
            f"Error al consultar Context7: {e}",
        )
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Inferencia con Llama 3.1 (lectura NDJSON)
# ─────────────────────────────────────────────
async def ollama_reason(prompt: str):
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, json=payload, timeout=120) as resp:
            if resp.headers.get("content-type", "").startswith("application/x-ndjson"):
                # leer streaming NDJSON
                data = ""
                async for line in resp.content:
                    data += line.decode()
                # Ollama suele mandar objetos {"response": "..."}
                return data
            else:
                data = await resp.json()
                return data.get("response", str(data))

# ─────────────────────────────────────────────
# Razonamiento cognitivo global
# ─────────────────────────────────────────────
async def run_supervisor(task_id: str, user_prompt: str):
    """
    1️⃣  Consulta memoria (/memory/query)
    2️⃣  Llama a Context7 (estado del entorno)
    3️⃣  Fusiona ambas respuestas en un prompt analítico
    4️⃣  Llama a Llama3.1 (Ollama)
    5️⃣  Publica evento supervisor_reasoning
    """
    memory = await query_memory(user_prompt)
    context7_state = await query_context7(task_id, "/workspace")

    mem_summary = json.dumps(memory.get("summary", {}), ensure_ascii=False)
    ctx_summary = json.dumps(context7_state, ensure_ascii=False)

    reasoning_prompt = f"""
Eres un asistente de razonamiento cognitivo de un agente AI Developer.

Analiza la información disponible:

MEMORIA COGNITIVA (eventos previos):
{mem_summary}

ESTADO DEL PROYECTO (Context7):
{ctx_summary}

TAREA_ORIGINAL: "{user_prompt}"

1. Resume qué hizo el orquestador y el worker.
2. Explica el estado actual del proyecto (archivos, dependencias, coherencia).
3. Evalúa si el resultado fue exitoso o fallido.
4. Propón mejoras o próximos pasos.

Devuelve la respuesta en texto plano.
"""

    result = await ollama_reason(reasoning_prompt)

    # Registrar razonamiento final en Kafka
    send_state_update(
        task_id,
        "supervisor_reasoning",
        result,
    )
    return result

# ─────────────────────────────────────────────
# Utilidad para pruebas manuales dentro del contenedor
# ─────────────────────────────────────────────
if __name__ == "__main__":
    prompt = "print hola mundo en python"
    asyncio.run(run_supervisor(str(uuid4()), prompt))
