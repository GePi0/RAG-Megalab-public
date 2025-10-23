# orchestrator/file_writer.py
"""
file_writer.py – Intelligent File Writer v1.1
---------------------------------------------
Decide dinámicamente el formato del archivo en función de:
  • prompt del usuario
  • metadatos devueltos por el Worker
  • análisis del contenido generado
Guarda el archivo en workdir/ y publica eventos de I/O.
---------------------------------------------
"""

import re
import json
from datetime import datetime
from pathlib import Path
from incident_logger import log_incident
from state_producer import send_state_update


# --------------------- Inferencia -----------------------------

def infer_extension(prompt: str, worker_resp: dict, content: str) -> str:
    """Infere extensión probable según tres fuentes."""
    votes = {"py": 0, "json": 0, "md": 0, "csv": 0, "txt": 0}

    prompt_low = prompt.lower()
    if re.search(r"\.py|python", prompt_low):
        votes["py"] += 0.4
    if re.search(r"\.json|json", prompt_low):
        votes["json"] += 0.4
    if re.search(r"\.md|markdown", prompt_low):
        votes["md"] += 0.4
    if re.search(r"\.csv|csv", prompt_low):
        votes["csv"] += 0.4

    # Worker metadata
    for k, v in worker_resp.items():
        s = str(v).lower()
        if "python" in s:
            votes["py"] += 0.4
        if "json" in s:
            votes["json"] += 0.4
        if "markdown" in s or "md" in s:
            votes["md"] += 0.4
        if "csv" in s:
            votes["csv"] += 0.4

    # Content heuristics
    content_low = content.lower()
    if re.search(r"def |class |import ", content_low):
        votes["py"] += 0.2
    elif re.match(r"\s*[{[].*[}\]]\s*$", content_low, re.DOTALL):
        votes["json"] += 0.2
    elif re.match(r"^# |^## ", content_low, re.MULTILINE):
        votes["md"] += 0.2
    elif re.search(r",.*\n", content_low):
        votes["csv"] += 0.2
    else:
        votes["txt"] += 0.2

    ext = max(votes, key=votes.get)
    return ext or "txt"


# --------------------- Escritura -------------------------------

def write_worker_result_intelligent(project_id: str, prompt: str, worker_resp: dict) -> Path:
    """Crea archivo físico con extensión inferida."""
    project_root = Path(f"/workspace/projects/{project_id}")
    workdir = project_root / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    # Contenido + metadatos
    content = worker_resp.get("result") or "(sin contenido)"
    ext = infer_extension(prompt, worker_resp, content)

    suggested = "output"
    for k in ("file", "filename", "name"):
        if k in worker_resp:
            suggested = Path(str(worker_resp[k])).stem
            break

    filename = f"{suggested}_{datetime.now().strftime('%H%M%S')}.{ext}"
    path = workdir / filename

    try:
        path.write_text(content, encoding="utf-8")
        log_incident("file_writer", "INFO", "file_created",
                     f"Archivo {filename} ({ext}) generado en {workdir}")
        send_state_update(
            "FILE_WRITER",
            "workdir_file_created",
            f"Archivo {filename}",
            extras={
                "project": project_id,
                "file_path": str(path),
                "ext": ext,
                "size": path.stat().st_size,
            },
        )
    except Exception as e:
        log_incident("file_writer", "ERROR", "file_write_failure",
                     f"Error escribiendo archivo {filename}: {e}")
        raise
    return path
