"""
worker_client.py
Cliente HTTP para comunicación con el Worker_MCP (en megalab_net).
"""

import os
import requests
from typing import Any, Dict

WORKER_URL = os.getenv("WORKER_URL", "http://worker_mcp:8003")
DEFAULT_PATH = "/act"  # endpoint real del Worker
WORKER_TIMEOUT = int(os.getenv("WORKER_TIMEOUT", 60))

def send_task_to_worker(task_id: str, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Envía tarea al Worker MCP.
    Retorna el JSON de respuesta o marca worker_status: failed.
    """
    payload = {"task_id": task_id, "task": task, "context": context}
    try:
        r = requests.post(f"{WORKER_URL}{DEFAULT_PATH}", json=payload, timeout=WORKER_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "task_id": task_id,
            "result": "(no result)",
            "context": {**context, "worker_status": "failed", "error": str(e)},
        }
