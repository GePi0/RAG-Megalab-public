from chromadb import PersistentClient
from elasticsearch import Elasticsearch


class MemoryQueryEngine:
    def __init__(self, chroma_path: str, es_host: str = "http://elasticsearch:9200"):
        """
        Inicializa clientes de Chroma y ElasticSearch.
        """
        self.chroma = PersistentClient(path=chroma_path)
        self.es = Elasticsearch(es_host)

    # ----------------------------------------------------
    # Consulta vectorial → Chroma (memoria semántica)
    # ----------------------------------------------------
    def query_chroma(self, text_query: str, k: int = 5):
        """
        Realiza búsqueda por similitud en la colección 'state_memory'.
        Devuelve los k documentos más parecidos al texto consultado.
        """
        collection = self.chroma.get_or_create_collection("state_memory")
        result = collection.query(
            query_texts=[text_query],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        print(
            f"🔎  Chroma devolvió {len(result.get('ids', [[]])[0]) if result.get('ids') else 0} "
            f"documentos (top‑{k})."
        )
        return result

    # ----------------------------------------------------
    # Consulta estructurada → Elastic (memoria temporal)
    # ----------------------------------------------------

    def query_elastic(self, task_ids: list[str]):
        """
        Busca en Elastic todos los eventos asociados a los task_ids detectados en Chroma.
        Usa 'terms' (exacto) y cae en 'match' si falla.
        """
        # Filtrado de valores nulos o vacíos
        task_ids = [t for t in task_ids if t and t.lower() != "null"]
        if not task_ids:
            print("⚠️  Sin task_ids válidos para consultar en Elastic.")
            return []

        print(f"🔍  Buscando en Elastic {len(task_ids)} task_ids: {task_ids}")

        # ---------- Query principal: terms exacto ----------
        query_terms = {
            "query": {"terms": {"task_id.keyword": task_ids}},
            "sort": [{"@timestamp": {"order": "asc"}}],
            "size": 500,
        }

        try:
            res = self.es.search(index="state_manager_v1", body=query_terms)
            hits = [hit["_source"] for hit in res["hits"]["hits"]]
            if hits:
                print(f"✅  Elastic devolvió {len(hits)} eventos (terms).")
                return hits

            # ---------- Fallback si no hubo coincidencias ----------
            should = [{"match": {"task_id": t}} for t in task_ids]
            query_match = {
                "query": {"bool": {"should": should}},
                "sort": [{"@timestamp": {"order": "asc"}}],
                "size": 500,
            }
            res = self.es.search(index="state_manager_v1", body=query_match)
            hits = [hit["_source"] for hit in res["hits"]["hits"]]
            print(f"✅  Elastic devolvió {len(hits)} eventos (match fallback).")
            return hits

        except Exception as e:
            print(f"⚠️  Error consultando Elastic: {e}")
            return []

    # ----------------------------------------------------
    # Unión cognitiva → Chroma + Elastic (versión adaptativa)
    # ----------------------------------------------------
    def run_hybrid_query(self, text_query: str, k: int = 5):
        """
        Combina resultados vectoriales (Chroma) con eventos cronológicos (Elastic).
        Selecciona adaptativamente task_ids válidos y, si ninguno es utilizable,
        emplea el más reciente del índice state_manager_v1.
        """
        # Paso 1 → búsqueda vectorial
        chroma_res = self.query_chroma(text_query, k)

        # Paso 2 → extraer y limpiar task_ids
        raw_ids = [
            md.get("task_id")
            for md in chroma_res.get("metadatas", [[]])[0]
            if md.get("task_id")
        ]
        task_ids = [tid for tid in raw_ids if tid.lower() != "null"]
        task_ids = list(dict.fromkeys(task_ids))  # eliminar duplicados manteniendo orden

        print(f"🧠  task_ids devueltos por Chroma: {task_ids}")

        # Paso 3 → fallback: si no hay ids válidos, coger el último task_id de Elastic
        if not task_ids:
            try:
                recent = self.es.search(
                    index="state_manager_v1",
                    body={
                        "sort": [{"@timestamp": {"order": "desc"}}],
                        "_source": ["task_id"],
                        "size": 1,
                    },
                )
                last_id = recent["hits"]["hits"][0]["_source"].get("task_id")
                if last_id:
                    task_ids = [last_id]
                    print(f"♻️  Fallback → usando último task_id en Elastic: {last_id}")
            except Exception as e:
                print(f"⚠️  No se pudo obtener fallback task_id: {e}")

        # Paso 4 → si varios, verificar cuáles existen aún en Elastic y priorizar recientes
        validated_ids = []
        for tid in task_ids:
            try:
                check = self.es.search(
                    index="state_manager_v1",
                    body={
                        "query": {"term": {"task_id.keyword": tid}},
                        "size": 1,
                    },
                )
                if check["hits"]["hits"]:
                    validated_ids.append(tid)
            except Exception:
                continue

        if not validated_ids and task_ids:
            validated_ids = [task_ids[0]]  # al menos uno para continuidad

        print(f"🧩  task_ids validados para cruce en Elastic: {validated_ids}")

        # Paso 5 → consulta a Elastic y combinación
        elastic_res = self.query_elastic(validated_ids)

        return {
            "contextual_docs": chroma_res,
            "timeline": elastic_res,
        }
