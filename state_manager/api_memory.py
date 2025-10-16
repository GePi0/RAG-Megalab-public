"""
api_memory.py
--------------------------------------------------------
Micro‑API de consulta cognitiva (FASE 8.1)
--------------------------------------------------------
• /memory/health  → comprueba servicio.
• /memory/query   → búsqueda semántica híbrida
                    (Chroma vector  +  Elastic timeline)
--------------------------------------------------------
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from query_engine import MemoryQueryEngine


# ===============================================
#  Configuración general de logging
# ===============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# ===============================================
#  Inicialización de servicios
# ===============================================
CHROMA_PATH = os.getenv("CHROMA_PATH", "/app/chroma")
ES_HOST = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")

try:
    engine = MemoryQueryEngine(chroma_path=CHROMA_PATH, es_host=ES_HOST)
    logging.info(f"✅  Conectado a Chroma ({CHROMA_PATH}) y Elastic ({ES_HOST})")
except Exception as e:
    logging.error(f"❌  Error inicializando motores: {e}")
    engine = None

app = FastAPI(
    title="🧠 Cognitive Memory API",
    description="Consulta inteligente a la memoria cognitiva (Elastic + Chroma).",
    version="1.0",
)


# ===============================================
#  Modelos de datos
# ===============================================
class QueryRequest(BaseModel):
    query: str
    k: int = 5


# ===============================================
#  Endpoints
# ===============================================
@app.get("/memory/health")
def health():
    return {"status": "ok", "chroma_path": CHROMA_PATH, "es_host": ES_HOST}


@app.post("/memory/query")
def memory_query(req: QueryRequest):
    if not engine:
        raise HTTPException(
            status_code=500,
            detail="Motor cognitivo no inicializado correctamente",
        )

    try:
        logging.info(f"🔎 Recibida query semántica: '{req.query}' (k={req.k})")

        result = engine.run_hybrid_query(req.query, req.k)

        if not result["contextual_docs"]["ids"]:
            return {
                "query": req.query,
                "result": {},
                "message": "Sin coincidencias en memoria cognitiva",
            }

        logging.info(
            f"✅ Query completada: {len(result['contextual_docs']['ids'][0])} docs • "
            f"{len(result['timeline'])} eventos timeline."
        )

        return {
            "query": req.query,
            "summary": {
                "docs": len(result["contextual_docs"]["ids"][0]),
                "events": len(result["timeline"]),
            },
            "result": result,
        }

    except Exception as e:
        logging.error(f"❌ Error en consulta cognitiva: {e}")
        raise HTTPException(status_code=500, detail=str(e))
