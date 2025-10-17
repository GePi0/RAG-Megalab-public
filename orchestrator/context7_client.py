# context7_client.py
import aiohttp, json, os

CONTEXT7_URL = os.getenv("CONTEXT7_URL", "http://context7:8099")

async def check_project_summary(path: str = "/workspace") -> dict:
    """Consulta estado general del proyecto."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CONTEXT7_URL}/status?path={path}") as r:
            return await r.json()

async def validate_file(file_path: str) -> dict:
    """Valida un archivo o módulo específico."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{CONTEXT7_URL}/validate?file={file_path}") as r:
            return await r.json()
