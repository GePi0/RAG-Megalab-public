# orchestrator/healing_manager.py
"""
healing_manager.py – FASE 14‑B
---------------------------------------------------------------
Auto‑curación semántica basada en meta‑reflexiones.
Analiza el texto generado por Llama 3.1, localiza patrones
de error y ejecuta reparaciones específicas mediante AutoRepair.
Registra cada acción en Elastic/Kafka.
---------------------------------------------------------------
"""

import re
from auto_repair import handle_restart
from incident_logger import log_incident
from state_producer import send_state_update
from kafka import KafkaConsumer
import json
import os

# 🔹 1️⃣ Diccionario de correspondencias (pattern → servicio)
PATTERN_MAP = {
    r"Error\s*code\s*-?32000": "context7",
    r"TimeoutError": "ollama-service",
    r"ConnectionRefused": "worker_mcp",
    r"Refused to connect": "worker_mcp",
    r"OSError.*docker": "orchestrator",
}


def parse_reflection_for_services(reflection_text: str) -> list[str]:
    """
    Escanea el texto de meta‑reflexión buscando patrones conocidos
    y devuelve una lista de servicios candidatos a reparación.
    """
    matches = []
    for pattern, service in PATTERN_MAP.items():
        if re.search(pattern, reflection_text, flags=re.IGNORECASE):
            matches.append(service)
    return list(set(matches))


def heal_from_reflection(reflection_text: str) -> None:
    """
    Decide y ejecuta acciones de reparación basadas en la meta‑reflexión.
    Publica eventos 'healing_attempted' y 'healing_success'.
    """
    services = parse_reflection_for_services(reflection_text)

    if not services:
        log_incident(
            "healing_manager",
            "INFO",
            "healing_skipped",
            "Ningún patrón de error relevante encontrado en meta‑reflexión.",
        )
        return

    for svc in services:
        log_incident(
            svc,
            "WARNING",
            "healing_triggered",
            f"HealingManager detectó patrón de fallo; se reiniciará {svc}",
        )
        try:
            result = handle_restart(svc)
            recovered = result.get("status") in ("restarted", "simulated")
            send_state_update(
                "HEALING",
                f"{svc}_healed",
                f"{svc} recuperado = {recovered}",
                {"recovered": recovered},
            )
            log_incident(
                svc,
                "INFO",
                "healing_result",
                f"Resultado de curación para {svc}",
                recovered=recovered,
            )
        except Exception as e:
            log_incident(
                svc,
                "ERROR",
                "healing_failed",
                f"Error al intentar reparar {svc}: {e}",
            )

def listen_state_for_errors():
    """
    Listener que detecta errores como 'context7_error' en el topic state_update
    y dispara curación inmediata (reinicio de servicio).
    Este listener complementa el healing semántico basado en meta‑reflexión.
    """
    broker = os.getenv("KAFKA_BROKER", "redpanda:9092")
    topic = os.getenv("STATE_TOPIC", "state_update")
    group_id = "healing_listener"

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=[broker],
            auto_offset_reset="latest",
            group_id=group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf‑8")),
        )
        print("🧩 [healing_manager] escuchando errores en state_update …")
    except Exception as e:
        print(f"❌ [healing_manager] No se ha podido conectar al broker Kafka: {e}")
        return

    for msg in consumer:
        data = msg.value
        stage = data.get("stage", "")
        if stage == "context7_error":
            log_incident(
                "context7",
                "WARNING",
                "healing_instant_trigger",
                "Detectado evento context7_error; ejecutando curación inmediata."
            )
            try:
                res = handle_restart("context7")
                recovered = res.get("status") in ("restarted", "simulated")
                log_incident(
                    "context7",
                    "INFO",
                    "healing_instant_result",
                    "Curación inmediata concluida.",
                    recovered=recovered,
                )
                send_state_update(
                    "HEALING",
                    "context7_healed",
                    "Reinicio curativo automático tras context7_error",
                    {"recovered": recovered},
                )
            except Exception as e:
                log_incident(
                    "context7",
                    "ERROR",
                    "healing_instant_failed",
                    f"Fallo al intentar curar context7: {e}",
                )
