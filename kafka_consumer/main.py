import json
import os
from kafka import KafkaConsumer

BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "rag_logs")

def safe_deserializer(raw):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None

def main():
    print(f"🚀 Listening to topic '{TOPIC}' on broker '{BROKER}'...\n")
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=[BROKER],
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="rag_monitor",
        value_deserializer=safe_deserializer,
    )

    for msg in consumer:
        event = msg.value
        if not event:
            continue  # ignora vacíos
        print("📦 EVENT ----------------------------")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        print("------------------------------------\n")

if __name__ == "__main__":
    main()
