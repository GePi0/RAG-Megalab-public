from fastapi import FastAPI, HTTPException, Query
from context_db import ChromaContextDB
from schemas import ContextAddRequest
import os

app = FastAPI(title="Context Service", version="1.0")

# === Configuración desde variables de entorno ===
DB_PATH = os.getenv("CHROMA_DB_PATH", "/app/chroma")
COLLECTION = os.getenv("CHROMA_COLLECTION", "rag_contexts")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# === Inicialización de BD vectorial ===
context_db = ChromaContextDB(DB_PATH, COLLECTION, EMBED_MODEL)


@app.post("/add")
def add_context(entry: ContextAddRequest):
    """Guarda un nuevo contexto (texto + metadatos) en la base Chroma."""
    try:
        context_db.add_text(entry.text, entry.metadata)
        return {"status": "ok", "stored_in": COLLECTION}
    except Exception as e:
        import traceback
        print("💥 ERROR en /add:")
        print(traceback.format_exc())          # 👈 muestra el stack completo en docker logs
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query")
def query_context(
    query_text: str = Query(..., description="Texto de consulta"),
    k: int = Query(3, description="Número de resultados a devolver"),
):
    """Consulta por similitud semántica."""
    try:
        results = context_db.query_similar(query_text, k)
        return {"results": results}
    except Exception as e:
        import traceback
        print("💥 ERROR en /query:")
        print(traceback.format_exc())          # 👈 idem
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Verifica que el servicio está corriendo y la colección existe."""
    return {"service": "context_service", "collection": COLLECTION, "status": "healthy"}
