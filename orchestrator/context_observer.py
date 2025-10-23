# orchestrator/context_observer.py
"""
FASE 12 – Context Awareness 2.0
-----------------------------------------------
Escanea el entorno local de un proyecto
y genera un resumen (archivos + dependencias).
Publica el resultado al topic `state_update`.
-----------------------------------------------
"""

import os
import hashlib
import json
import re
from pathlib import Path
from state_producer import send_state_update


def hash_file(path: Path) -> str:
    """Calcula hash corto para detectar cambios."""
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        return "unreadable"
    return h.hexdigest()[:12]


def scan_project(project_path: str) -> dict:
    """
    Recorre todas las carpetas del proyecto y devuelve un resumen.
    """
    base = Path(project_path)
    files_data, deps = [], set()

    for root, _, files in os.walk(base):
        for f in files:
            fp = Path(root) / f
            rel = fp.relative_to(base).as_posix()
            try:
                sz = fp.stat().st_size
                ts = fp.stat().st_mtime
            except Exception:
                sz, ts = 0, 0
            files_data.append(
                {"file": rel, "size": sz, "mtime": ts, "hash": hash_file(fp)}
            )
            # extraccion mínima de dependencias
            if f.endswith(".py"):
                try:
                    text = fp.read_text(errors="ignore")
                    for imp in re.findall(r"(?m)^(?:from|import)\s+(\w+)", text):
                        deps.add(imp)
                except Exception:
                    pass

    summary = {
        "project": base.name,
        "num_files": len(files_data),
        "dependencies": sorted(list(deps)),
        "files": files_data,
    }

    # publica a Kafka/Elastic
    send_state_update(
        "CONTEXT_OBSERVER",
        "project_scan_ok",
        f"Escaneado {base.name} con {len(files_data)} archivos",
        extras={"summary": summary},
    )
    print(f"🧩 Context Awareness → {base.name}: {len(files_data)} archivos detectados")
    evaluate_awareness(summary)
    return summary

# --- Reglas de observación y alertas ----------------------------
def evaluate_awareness(summary: dict) -> list[dict]:
    """
    Aplica reglas básicas sobre el resumen del proyecto.
    Devuelve lista de alertas generadas.
    """
    alerts = []
    files = summary.get("files", [])
    deps = summary.get("dependencies", [])

    # ❗ Regla 1 – Archivos demasiado grandes o vacíos
    for f in files:
        if f["size"] == 0:
            alerts.append({"type": "empty_file", "file": f["file"], "msg": "Archivo vacío"})
        if f["size"] > 5 * 1024 * 1024:
            alerts.append({"type": "oversized_file", "file": f["file"], "msg": "Archivo >5MB"})

    # ❗ Regla 2 – Faltan archivos esenciales
    names = [f["file"] for f in files]
    if not any("README" in n.upper() for n in names):
        alerts.append({"type": "missing_readme", "msg": "No se encontró README en el proyecto"})
    if not any(n.startswith("workdir/") for n in names):
        alerts.append({"type": "missing_workdir", "msg": "El directorio workdir está vacío"})

    # ❗ Regla 3 – Dependencias sin requirements.txt
    if "requirements.txt" not in names and deps:
        alerts.append({
            "type": "deps_unlisted",
            "missing": deps,
            "msg": "Se detectaron dependencias pero falta requirements.txt"
        })

    # Publicar los resultados (si hay alertas)
    if alerts:
        send_state_update(
            "CONTEXT_OBSERVER",
            "context_alert",
            f"{len(alerts)} anomalías detectadas en {summary['project']}",
            extras={"alerts": alerts, "project": summary["project"]},
        )
        print(f"⚠️ Context Alerts → {summary['project']}: {len(alerts)} detectadas")
    else:
        print(f"✅ Context Alerts → {summary['project']}: ningún problema detectado")

    return alerts
