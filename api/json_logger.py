from kafka import KafkaProducer
import json, datetime, os

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "rag_logs_v2")

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    acks="all",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

def log_event(service, level, event, message, **kwargs):
    log = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": service,
        "level": level.upper(),
        "event": event,
        "message": message,
        "extras": kwargs,
    }
    try:
        producer.send(KAFKA_TOPIC, value=log)
        producer.flush()
    except Exception as e:
        print(f"[logger] Kafka error: {e}")
