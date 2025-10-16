import json
import datetime
import os
from kafka import KafkaProducer

LOG_DIR = os.getenv("LOG_DIR", "/app/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "events.log")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "rag_logs")

try:
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        acks="all",
        linger_ms=10,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    kafka_ready = True
    print(f"✅ [logger] Kafka conectado a {KAFKA_BROKER}")
except Exception as e:
    print(f"⚠️ [logger] Kafka no disponible: {e}")
    kafka_ready = False


def log_event(service: str, level: str, event: str, message: str, **kwargs):
    """
    Envía logs estructurados → archivo local + topic Kafka (Redpanda).
    """
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": service,
        "level": level.upper(),
        "event": event,
        "message": message,
        "extras": kwargs,
    }

    line = json.dumps(log_entry, ensure_ascii=False)

    # --- salida visible ---
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    # --- envío asíncrono a Redpanda ---
    if kafka_ready:
        try:
            producer.send(KAFKA_TOPIC, value=log_entry)
            producer.flush()
        except Exception as e:
            print(f"⚠️ [logger] error enviando a Kafka: {e}")
