import os
from chromadb import PersistentClient
from langchain_community.embeddings import OllamaEmbeddings


class ChromaContextDB:
    """Gestor local de persistencia semántica con ChromaDB + embeddings."""

    def __init__(self, db_path: str, collection_name: str, embed_model: str):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embed_model = embed_model
        self.client = PersistentClient(path=db_path)

        # Inicialización automática
        if collection_name not in [
            c.name for c in self.client.list_collections()
        ]:
            print(f"🧪 [init] creando colección '{collection_name}' ...")
            self.collection = self.client.create_collection(name=collection_name)
        else:
            self.collection = self.client.get_collection(name=collection_name)

        # Modelo de embeddings
        self.embeddings = OllamaEmbeddings(model=self.embed_model, base_url="http://ollama-service:11434")
        print(f"✅ ChromaDB inicializada → {self.db_path} | colección: {self.collection_name}")

    # === Funciones básicas ===
    def add_text(self, text: str, metadata: dict):
        """Inserta texto + metadatos."""
        vectors = self.embeddings.embed_documents([text])
        doc_id = metadata.get("id") or str(len(self.collection.get()["ids"]) + 1)
        self.collection.add(ids=[doc_id], embeddings=vectors, metadatas=[metadata], documents=[text])

    def query_similar(self, query_text: str, k: int = 3):
        """Devuelve los k contextos más similares al texto indicado."""
        query_vec = self.embeddings.embed_query(query_text)
        results = self.collection.query(query_embeddings=[query_vec], n_results=k)
        formatted = [
            {"id": rid, "text": doc, "score": score, "metadata": meta}
            for rid, doc, score, meta in zip(
                results["ids"][0], results["documents"][0], results["distances"][0], results["metadatas"][0]
            )
        ]
        return formatted
