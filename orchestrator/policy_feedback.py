"""
policy_feedback.py
---------------------------------------------------
Evalúa los últimos eventos de State Manager (Elastic)
y actualiza los pesos de las políticas cognitivas
en función de éxitos o fallos recientes.
---------------------------------------------------
"""

import os
import datetime
import yaml
import requests
import numpy as np
import json
from kafka import KafkaConsumer

ELASTIC_URL = os.getenv(
    "ELASTIC_URL", "http://elasticsearch:9200/state_manager_v1/_search"
)
POLICIES_FILE = "/app/policies/rules.yml"

# ===============================================================
# 🧱 1️⃣ Recuperar eventos recientes desde Elastic
# ===============================================================
def fetch_recent_events(n: int = 100):
    """Lee los últimos N eventos de tareas recientes."""
    query = {
        "size": n,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": ["stage", "message", "@timestamp"],
    }

    r = requests.post(ELASTIC_URL, json=query, timeout=10)
    data = r.json()
    hits = data.get("hits", {}).get("hits", [])
    return [h["_source"] for h in hits if "_source" in h]


# ===============================================================
# 🧮 2️⃣ Calcular score de refuerzo
# ===============================================================
def compute_feedback(events: list[dict]) -> float:
    """
    Usa una heurística simple para calcular refuerzo global:
      +0.01 por task_complete,
      +0.02 si también aparece context7_checked antes de éxito,
      -0.01 por execution_error o supervisor_error,
      -0.005 si context7_used y aun así falla.
    """
    score = 0.0
    for e in events:
        stage = e.get("stage", "")
        if stage == "task_complete":
            score += 0.01
        elif stage == "context7_checked":
            score += 0.02
        elif stage in ["execution_error", "supervisor_error"]:
            score -= 0.01
        elif "context7" in stage and "error" in e.get("message", "").lower():
            score -= 0.005
    return float(np.clip(score, -0.05, 0.05))  # evita saltos bruscos


# ===============================================================
# 🧭 3️⃣ Actualizar pesos en /app/policies/rules.yml
# ===============================================================

def update_policy_weights(score: float):
    """
    Ajusta gradualmente los pesos en un bloque paralelo 'weights'
    sin modificar la estructura textual de las policies.
    """
    if not os.path.exists(POLICIES_FILE):
        print(f"⚠️ Policy file not found: {POLICIES_FILE}")
        return

    with open(POLICIES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "rules" not in data:
        print("⚠️ No rules found to update.")
        return

    now = datetime.datetime.utcnow().isoformat()
    α = 0.05  # learning rate
    decay = 0.9

    # Creamos bloque "weights" si no existía
    if "weights" not in data:
        data["weights"] = {}

    weights = data["weights"]

    # Recorre todas las líneas de avoid/prefer
    for group in ("avoid", "prefer"):
        if group not in data["rules"]:
            continue
        for line in data["rules"][group]:
            key = f"{group}:{line.strip()[:80]}"  # hash parcial por texto
            w_old = weights.get(key, 0.5)
            w_new = decay * w_old + (1 - decay) * (w_old + α * np.sign(score))
            w_new = float(np.clip(w_new, 0.0, 1.0))
            weights[key] = round(w_new, 4)

    data["weights_meta"] = {
        "last_update": now,
        "last_score": round(score, 4),
    }

    with open(POLICIES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

    trend = "↑" if score > 0 else "↓" if score < 0 else "→"
    print(f"✅ Policy Feedback actualizado {trend}  (Δ={score:+.3f})")

# ===============================================================
# 🚀 4️⃣ Pipeline completo
# ===============================================================
def run_policy_feedback():
    print(f"🧠 [Feedback] Leyendo eventos recientes de Elastic...")
    events = fetch_recent_events(100)
    if not events:
        print("⚠️ Ningún evento encontrado.")
        return
    score = compute_feedback(events)
    update_policy_weights(score)
    print("✅ [Feedback] Actualización completada.")


if __name__ == "__main__":
    run_policy_feedback()

# --- Integración Health Feedback (FASE 14‑B) ----------------

def listen_health_feedback():
    """Consume eventos health_status y ajusta pesos de resiliencia."""
    topic = os.getenv("KAFKA_HEALTH_TOPIC", "health_status")
    broker = os.getenv("KAFKA_BROKER", "redpanda:9092")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=[broker],
        auto_offset_reset="latest",
        group_id="policy_feedback_health",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    print("🧠 [feedback] escuchando health_status para adaptar rules.yml")
    for msg in consumer:
        data = msg.value
        service, level, event = (
            data.get("service"),
            data.get("level"),
            data.get("event"),
        )
        if not service:
            continue

        # --- regla sencilla de refuerzo ---
        delta = 0
        if event == "health_ok":
            delta = +0.01
        elif event == "health_fail":
            delta = -0.02
        elif event.startswith("auto_repair"):
            delta = +0.02

        if delta != 0:
            from policy_adapter import modify_weight
            old_val = modify_weight("resilience", delta)
            # Solo imprime cuando hay cambio real (<1.0)
            if old_val < 0.999:
                print(f"🧩 [feedback] ajuste resiliencia {service}: Δ{delta:+.02f}")
