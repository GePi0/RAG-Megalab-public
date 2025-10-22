"""
project_manager/snapshot_manager.py
----------------------------------------------------
Guarda versiones del workdir antes de cada modificación
y permite 'undo' restaurando snapshots previos.
----------------------------------------------------
"""
import os, zipfile, datetime, shutil

BASE_PATH = "/workspace/projects"

def create_snapshot(project_id: str):
    workdir = os.path.join(BASE_PATH, project_id, "workdir")
    snapdir = os.path.join(BASE_PATH, project_id, "versions")
    os.makedirs(snapdir, exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("snap_%Y%m%d_%H%M%S")
    snapfile = os.path.join(snapdir, f"{stamp}.zip")
    with zipfile.ZipFile(snapfile, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(workdir):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, workdir)
                zipf.write(full, rel)
    print(f"📦 Snapshot creado: {snapfile}")
    return snapfile

def restore_last_snapshot(project_id: str):
    snapdir = os.path.join(BASE_PATH, project_id, "versions")
    snaps = sorted(os.listdir(snapdir))
    if not snaps:
        print("⚠️ No hay snapshots para restaurar.")
        return
    last_snap = os.path.join(snapdir, snaps[-1])
    workdir = os.path.join(BASE_PATH, project_id, "workdir")
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    with zipfile.ZipFile(last_snap, "r") as zipf:
        zipf.extractall(workdir)
    print(f"↩️  Restaurado snapshot: {last_snap}")
    return last_snap
