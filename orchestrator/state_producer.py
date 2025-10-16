"""
state_producer.py
----------------------------------------------------
Productor Kafka para enviar "snapshots cognitivos"
al topic `state_update`, consumido por el State Manager.
----------------------------------------------------
"""

from kafka import KafkaProducer
import json, os, datetime

# Lee configuración desde entorno (misma red de Kafka)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "redpanda:9092")
STATE_TOPIC  = os.getenv("STATE_TOPIC", "state_update")

# Instancia global del productor
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    acks="all",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

def send_state_update(task_id: str, stage: str, message: str, extras: dict | None = None):
    """
    Envía una actualización de estado cognitivo (nivel alto) al topic `state_update`.

    Args:
        task_id  : ID único de la tarea o prompt.
        stage    : Fase o evento (context_persisted, worker_done, error, etc.).
        message  : Texto semántico / resumen.
        extras   : Diccionario opcional con contexto adicional.
    """
    payload = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "service": "orchestrator",
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
