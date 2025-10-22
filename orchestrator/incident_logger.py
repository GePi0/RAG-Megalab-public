# orchestrator/incident_logger.py
"""
incident_logger.py – Sistema de registro auditable de incidentes (FASE 14‑A)
---------------------------------------------------------------------------
Guarda eventos de fallos y reparaciones en:
  • Archivo local  /storage/logs/orchestrator/incidents.log
  • ElasticSearch  índice  incident_events_v1
---------------------------------------------------------------------------
"""

import json
import os
import datetime
import requests
from kafka import KafkaProducer

LOG_DIR = os.getenv("LOG_DIR", "/storage/logs/orchestrator")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "incidents.log")

ELASTIC_URL = os.getenv("ELASTIC_URL", "http://elasticsearch:9200")
ELASTIC_INDEX = os.getenv("ELASTIC_INDEX_INCIDENTS", "incident_events_v1")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC = os.getenv("KAFKA_HEALTH_TOPIC", "health_status")

# Reutilizamos Kafka para trazabilidad fast
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda v: json.dumps(v).encode("utf‑8"),
    acks="all",
)

def log_incident(service: str, level: str, event: str, message: str, **extras):
    """
    Registra un incidente estructurado.
    level: INFO | WARNING | ERROR | CRITICAL
    """
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": service,
        "level": level,
        "event": event,
        "message": message,
        "extras": extras,
    }

    # --- Archivo local
    with open(LOG_FILE, "a", encoding="utf‑8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # --- Envío a Elastic (best‑effort)
    try:
        requests.post(f"{ELASTIC_URL}/{ELASTIC_INDEX}/_doc", json=entry, timeout=2)
    except Exception:
        pass

    # --- Publicación en Kafka para observabilidad
    try:
        producer.send(KAFKA_TOPIC, value=entry)
        producer.flush()
    except Exception:
        pass

    if level != "INFO":
        print(f"🩺 [incident_logger] {level}: {service} → {event}")
    return entry
