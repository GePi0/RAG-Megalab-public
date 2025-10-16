import requests
import json
import datetime
import os

# Endpoint del servicio de contexto (usa red host)
CONTEXT_URL = os.getenv(
    "CONTEXT_SERVICE_URL",
    "http://context_service:8002/add",  # endpoint directo
)


def store_context_entry(text: str, metadata: dict = None):
    """
    Envía un texto y metadatos al servicio de contexto (ChromaDB).
    Mantiene trazabilidad de prompts y respuestas.
    """
    if metadata is None:
        metadata = {}

    # Enriquecer con info básica (timestamp, origen, etc.)
    entry = {
        "text": text,
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            **metadata,
        },
    }

    try:
        res = requests.post(CONTEXT_URL, json=entry, timeout=10)
        if res.status_code == 200:
            print(f"🧠 [context] guardado en Chroma ({metadata.get('role', 'unknown')})")
        else:
            print(f"⚠️ [context] error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ [context] fallo al enviar contexto: {e}")
