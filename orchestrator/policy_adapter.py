"""
policy_adapter.py
---------------------------------------------------
Convierte las políticas cognitivas (meta_reflection)
en reglas adaptativas útiles para ajustar prompts.
---------------------------------------------------
"""

import aiohttp
import os
import datetime
import yaml
import json
import re
from pathlib import Path

ELASTIC_URL = os.getenv(
    "ELASTIC_URL", "http://elasticsearch:9200/state_manager_v1/_search"
)
RULES_PATH = Path("/app/policies/rules.yml")  # dentro del contenedor orchestrator


# ============================================================
# 🔸 1️⃣ Leer las últimas políticas meta_reflection
# ============================================================
async def fetch_recent_policies(n: int = 5) -> list[str]:
    """Recupera las últimas N entradas stage:meta_reflection desde Elastic."""
    query = {
        "size": n,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {"term": {"stage.keyword": "meta_reflection"}},
        "_source": ["message", "@timestamp"],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(ELASTIC_URL, json=query, timeout=20) as r:
            data = await r.json()
            hits = data.get("hits", {}).get("hits", [])
            return [h["_source"]["message"] for h in hits if "message" in h["_source"]]


# ============================================================
# 🔹 2️⃣ Analizar el texto y crear reglas simples
# ============================================================
def synthesize_prompt_rules(policies: list[str]) -> dict:
    """
    Analiza lenguaje natural para deducir reglas básicas.
    Usa heurísticas simples (palabras clave) para generar lists.
    """
    avoid, prefer = set(), set()

    for text in policies:
        lines = text.splitlines()
        for line in lines:
            line_low = line.lower().strip("-• ")
            if any(x in line_low for x in ["evitar", "no deber", "fallo", "error"]):
                avoid.add(line.strip())
            if any(x in line_low for x in ["repetir", "debería", "mejorar", "verificar"]):
                prefer.add(line.strip())

    return {
        "date_generated": datetime.datetime.utcnow().isoformat(),
        "rules": {"avoid": sorted(list(avoid)), "prefer": sorted(list(prefer))},
    }


# ============================================================
# 🔹 3️⃣ Guardar reglas en YAML
# ============================================================
def export_rules_to_yaml(rules: dict, path: Path = RULES_PATH):
    """Serializa las reglas a YAML persistente."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(rules, f, allow_unicode=True)
    print(f"✅ PolicyAdapter: reglas adaptativas exportadas → {path}")


# ============================================================
# 🧠 4️⃣ Pipeline completo (fetch + synthesize + export)
# ============================================================
async def build_adaptive_policy():
    """Flujo principal para generar reglas adaptativas desde Elastic."""
    try:
        policies = await fetch_recent_policies(5)
        if not policies:
            print("⚠️  PolicyAdapter: no se encontraron políticas previas.")
            return

        rules = synthesize_prompt_rules(policies)
        export_rules_to_yaml(rules)
        return rules

    except Exception as e:
        print(f"❌ Error en PolicyAdapter: {type(e).__name__}: {e}")
        return None


# ============================================================
# 🔹 5️⃣ Loader (para ser usado por el Orchestrator)
# ============================================================
def load_adaptive_context(path: Path = RULES_PATH) -> str:
    """Convierte las reglas YAML en texto breve para prefijo del prompt."""
    if not path.exists():
        return ""

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    avoid = "\n".join(f"- {x}" for x in data["rules"].get("avoid", []))
    prefer = "\n".join(f"- {x}" for x in data["rules"].get("prefer", []))

    return f"""# Adaptive Cognitive Policy (auto‑generada)
El agente debe evitar:
{avoid}

El agente debe priorizar:
{prefer}
"""

# ============================================================
# 🔹 cada ciclo de auto‑curación actualiza automáticamente la “confianza” del sistema en su capacidad de mantenerse estable.
# ============================================================
def modify_weight(key: str, delta: float):
    """Ajusta ligeramente un peso en rules.yml."""
    import yaml, os, time
    path = "/app/policies/rules.yml"
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    weights = data.get("weights", {})
    current = weights.get(key, 0.5)
    new_val = max(0.0, min(1.0, round(current + delta, 3)))
    weights[key] = new_val
    data["weights"] = weights
    with open(path, "w") as f:
        yaml.safe_dump(data, f)
    if round(new_val, 3) != round(current, 3):
        print(f"📈 [policy_adapter] {key}: {current:.3f} → {new_val:.3f}")
    return new_val
