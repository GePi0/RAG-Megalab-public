"""
state_manager/main.py
-----------------------------------------------------
Consumer cognitivo que escucha:
  - state_update
  - task_feedback
  - conversation_history

✔️ Limpio: sin errores de decodificación ni telemetría.
✔️ Mantiene sincronizadas Elastic y Chroma.
-----------------------------------------------------
"""

from kafka import KafkaConsumer
from elasticsearch import Elasticsearch, helpers
from chromadb import PersistentClient
import json, os, time, datetime

# ============================================
#   Configuración de entorno
# ============================================
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"   # 🔹 silencia métricas de Chroma

BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
TOPICS = ["state_update", "task_feedback", "conversation_history"]
ES_URL = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "state_manager_v1")
CHROMA_PATH = "/app/chroma"

# ============================================
#   Funciones auxiliares
# ============================================
def safe_deserializer(v: bytes):
    """Evita caídas al leer bytes mal formateados o vacíos"""
    if not v:
        return None
    try:
        return json.loads(v.decode("utf-8"))
    except Exception:
        return None  # 🔹 suprime aviso, ignora mensaje corrupto

# ============================================
#   Inicialización
# ============================================
consumer = KafkaConsumer(
    *TOPICS,
    bootstrap_servers=[BROKER],
    value_deserializer=safe_deserializer,
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="state_manager_cg",
)

es = Elasticsearch(ES_URL, verify_certs=False)

try:
    chroma = PersistentClient(path=CHROMA_PATH)
    collection = (
        chroma.get_collection("state_memory")
        if "state_memory" in [c.name for c in chroma.list_collections()]
        else chroma.create_collection("state_memory")
    )
    chroma_ready = True
except Exception as e:
    chroma_ready = False
    print(f"⚠️  No se pudo inicializar ChromaDB: {e}")

print(f"🧠  State Manager escuchando  →  {TOPICS}")

# ============================================
#   Bucle principal
# ============================================
while True:
    try:
        batch = []
        polled = consumer.poll(timeout_ms=2000)
        if not polled:
            continue

        for _, msgs in polled.items():
            for record in msgs:
                data = record.value
                if not data:
                    continue

                data["@timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
                data["source_topic"] = record.topic
                batch.append({"_index": ES_INDEX, "_source": data})

                if chroma_ready and "message" in data:
                    try:
                        collection.add(
                            ids=[f"{record.topic}-{time.time()}"],
                            documents=[data["message"]],
                            metadatas=[{
                                 "topic": record.topic,
                                 "service": str(data.get("service", "unknown")),
                                 "stage": str(data.get("stage", "null")),
				 "task_id": str(data.get("task_id", "null")),
				 "event": str(data.get("event", "null"))
                            }],
                        )
                    except Exception as e:
                        print(f"⚠️  Error al guardar en Chroma: {e}")

                print(f"📥 {record.topic:<22} ← {data.get('service')} : {data.get('stage') or data.get('event')}")

        if batch:
            helpers.bulk(es, batch)
            print(f"✅ Guardados {len(batch)} eventos en {ES_INDEX}")

    except Exception as e:
        print(f"⚠️  Loop error: {e}")
        time.sleep(2)
