"""
context7_client.py
----------------------------------------------------
Cliente asíncrono para consultar el servidor MCP Context7.
Permite validar archivos o módulos antes de su edición.
----------------------------------------------------
"""

import aiohttp
import os

# Context7 escucha internamente en 8080 (red de Docker)
CONTEXT7_URL = os.getenv("CONTEXT7_URL", "http://context7:8080/mcp")


async def validate_file(task_id: str, file_path: str) -> dict:
    """
    Llama a Context7 (JSON-RPC) para validar un archivo específico.
    Retorna un diccionario con el resultado (texto crudo o error).

    Args:
        task_id   : ID de la tarea en curso.
        file_path : ruta del archivo a analizar.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "validate",
        "params": {"file": file_path},
        "id": task_id,
    }
    headers = {"Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                CONTEXT7_URL, json=payload, headers=headers, timeout=30
            ) as resp:
                text = await resp.text()
                return {"status": "ok", "raw": text[:1024]}  # recorte de seguridad
    except Exception as e:
        return {"status": "error", "error": str(e)}
