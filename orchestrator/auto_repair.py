# orchestrator/auto_repair.py
"""
auto_repair.py – Reinicio selectivo de contenedores (FASE 14‑A)
---------------------------------------------------------------
Puede operar en dos modos:
  • dry_run=True  👉  sólo registra intención
  • dry_run=False 👉  ejecuta restart real vía Docker SDK
Publica resultados en Kafka y en incident_logger.
---------------------------------------------------------------
"""

import os
import time
import docker
from incident_logger import log_incident

DOCKER_SDK_ACTIVE = os.getenv("DOCKER_SDK_ACTIVE", "false").lower() == "true"
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

class AutoRepair:
    def __init__(self):
        if DOCKER_SDK_ACTIVE:
            self.client = docker.from_env()
        else:
            self.client = None

    def restart_service(self, service_name: str):
        start_t = time.time()
        if DRY_RUN or not DOCKER_SDK_ACTIVE:
            log_incident(
                service_name,
                "INFO",
                "auto_repair_simulated",
                f"Simulación de reinicio de {service_name}",
                dry_run=True,
            )
            return {"service": service_name, "status": "simulated"}

        try:
            container = self.client.containers.get(service_name)
            container.restart()
            duration = int((time.time() - start_t) * 1000)
            log_incident(
                service_name,
                "INFO",
                "auto_repair_executed",
                f"Contenedor reiniciado correctamente.",
                dry_run=False,
                duration_ms=duration,
            )
            return {"service": service_name, "status": "restarted", "duration_ms": duration}
        except Exception as e:
            duration = int((time.time() - start_t) * 1000)
            log_incident(
                service_name,
                "CRITICAL",
                "auto_repair_failed",
                f"Error reiniciando {service_name}: {e}",
                duration_ms=duration,
            )
            return {"service": service_name, "status": "failed", "error": str(e)}

# Utilidad directa
def handle_restart(service: str):
    """Función rápida usada por health_manager."""
    ar = AutoRepair()
    return ar.restart_service(service)
