"""
state_producer.py
-----------------------------------------------------
Envia actualizaciones de estado del Worker MCP
al topic Kafka `state_update`.
-----------------------------------------------------
"""
from kafka import KafkaProducer
import os, json, datetime

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
STATE_TOPIC = os.getenv("STATE_TOPIC", "state_update")

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    acks="all",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

def send_state_update(task_id: str, stage: str, message: str, extras: dict | None = None):
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": "worker_mcp",
        "task_id": task_id,
        "stage": stage,
        "message": message,
        "extras": extras or {},
    }
    try:
        producer.send(STATE_TOPIC, value=payload)
        producer.flush()
        print(f"🛰️  state_update → {stage} ({task_id})")
    except Exception as e:
        print(f"⚠️  Error enviando state_update: {e}")
