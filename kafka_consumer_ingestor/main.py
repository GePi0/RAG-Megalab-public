"""
Kafka → Elasticsearch Ingestor (Megalab Observability)
-----------------------------------------------------
Consume eventos JSON del topic Kafka y los indexa en Elasticsearch.

✔ Versión 2025-10 compatible con Redpanda + Elastic 8.15
"""

import os
import json
import time
from datetime import datetime
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch, helpers

# 🔹 Configuración mediante variables de entorno
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "rag_logs_v2")
ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX", "rag_logs_v2")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))

# 🔹 Inicializa cliente Kafka
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="latest",
    enable_auto_commit=True,
    group_id="elastic_ingestor",
)

# 🔹 Inicializa cliente Elasticsearch
es = Elasticsearch(ELASTIC_URL, verify_certs=False)

def enrich(event: dict) -> dict:
    """Asegura campos clave para Grafana/Elastic."""
    if not event:
        return None
    enriched = dict(event)
    enriched["@timestamp"] = (
        event.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    )
    enriched["service"] = event.get("service", "unknown")
    enriched["level"] = event.get("level", "INFO")
    enriched["message"] = event.get("message", "")
    return enriched

print(f"📡 Ingestor activo ({KAFKA_BROKER} → {ELASTIC_URL}/{ELASTIC_INDEX})")

while True:
    batch = []
    records = consumer.poll(timeout_ms=1000)
    for _, msgs in records.items():
        for record in msgs:
            event = enrich(record.value)
            if event:
                batch.append({"_index": ELASTIC_INDEX, "_source": event})

    if batch:
        try:
            helpers.bulk(es, batch)
            print(f"✅ Ingestados {len(batch)} eventos en {ELASTIC_INDEX}")
        except Exception as e:
            print(f"⚠️ Error enviando bulk → {e}")
        batch.clear()
