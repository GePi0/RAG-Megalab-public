"""
strategy_manager.py
----------------------------------------------------
Lee los pesos actuales de las políticas cognitivo‑adaptativas,
decide qué estrategias aplicar en tiempo real y devuelve un
plan de ejecución al Orchestrator.
----------------------------------------------------
"""

import yaml
import os

POLICIES_FILE = "/app/policies/rules.yml"

# ============================================================
# 🔹 1️⃣ Leer y normalizar pesos
# ============================================================
def load_policy_weights():
    """Carga las políticas y devuelve diccionario {texto: peso} ordenado."""
    if not os.path.exists(POLICIES_FILE):
        return {}

    with open(POLICIES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    weights = data.get("weights", {})
    return dict(sorted(weights.items(), key=lambda kv: kv[1], reverse=True))


# ============================================================
# 🔹 2️⃣ Seleccionar estrategias activas
# ============================================================
def select_strategies(weights: dict) -> dict:
    """
    Traduce las rules ponderadas en un plan práctico.
    Devuelve flags de decisión para el Orchestrator.
    """
    plan = {
        "use_context7": False,
        "validate_before_worker": False,
        "snapshot_before_write": True,
        "max_retries": 1,
    }

    for text, w in weights.items():
        lt = text.lower()
        if "context7" in lt and w > 0.55:
            plan["use_context7"] = True
        if "verificar" in lt or "configuración" in lt:
            if w > 0.5:
                plan["validate_before_worker"] = True
        if "errores" in lt and w > 0.6:
            plan["max_retries"] = 2

    return plan


# ============================================================
# 🔹 3️⃣ Aplicar estrategia (opcional logging)
# ============================================================
def apply_strategy(plan: dict, task_id: str):
    """Imprime / registra qué estrategias se activan."""
    actives = [k for k, v in plan.items() if v]
    text = f"🎯 Estrategias activas [{task_id}]: {', '.join(actives) or 'ninguna'}"
    print(text)
    return actives
