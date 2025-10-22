"""
project_manager/manifest.py
-----------------------------------------------------
Crea y mantiene manifiestos de proyectos:
  - estado, prompts, archivos, snapshots.
Permite saber en qué contexto de trabajo está cada tarea.
-----------------------------------------------------
"""
import os
import yaml
from datetime import datetime
from uuid import uuid4

BASE_PATH = "/workspace/projects"

def ensure_project_dir(project_id: str):
    p = os.path.join(BASE_PATH, project_id)
    os.makedirs(os.path.join(p, "input"), exist_ok=True)
    os.makedirs(os.path.join(p, "workdir"), exist_ok=True)
    os.makedirs(os.path.join(p, "versions"), exist_ok=True)
    os.makedirs(os.path.join(p, "logs"), exist_ok=True)
    return p

def create_manifest(prompt: str) -> str:
    """Crea un nuevo proyecto con manifest.yml inicial."""
    project_id = f"PROJECT-{uuid4().hex[:8]}"
    ensure_project_dir(project_id)
    manifest = {
        "project_id": project_id,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "prompts_history": [prompt],
        "undo_depth": 5,
    }
    path = os.path.join(BASE_PATH, project_id, "manifest.yml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f, allow_unicode=True)
    print(f"📁 Nuevo proyecto creado: {project_id}")
    return project_id

def append_prompt(project_id: str, prompt: str):
    """Añade nuevo prompt a un proyecto activo."""
    path = os.path.join(BASE_PATH, project_id, "manifest.yml")
    data = yaml.safe_load(open(path))
    data["prompts_history"].append(prompt)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

def close_project(project_id: str, status: str = "completed"):
    path = os.path.join(BASE_PATH, project_id, "manifest.yml")
    data = yaml.safe_load(open(path))
    data["status"] = status
    data["closed_at"] = datetime.utcnow().isoformat()
    yaml.safe_dump(data, open(path, "w"), allow_unicode=True)
    print(f"✅ Proyecto {project_id} marcado como '{status}'.")
