# ===========================================================
#  Kafka → Elasticsearch Ingestor  (Megalab Observability)
#  Autor: Gerard | Versión: 2025‑10
# ===========================================================

FROM python:3.10-slim

LABEL maintainer="Gerard <dev@megalab.local>"
LABEL description="Kafka → Elasticsearch Ingestor for RAG Megalab Observability"

# ---- Configuración base
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ---- Directorio de trabajo
WORKDIR /app

# ---- Dependencias
COPY requirements.txt /app/requirements.txt

RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Copia del código fuente
COPY main.py /app/

# ---- Variables por defecto (pueden sobrescribirse desde Compose)
ENV KAFKA_BROKER=redpanda:9092 \
    KAFKA_TOPIC=rag_logs_v2 \
    ELASTIC_URL=http://elasticsearch:9200 \
    ELASTIC_INDEX=rag_logs_v2 \
    BATCH_SIZE=100

# ---- Ejecutable por defecto
CMD ["python", "main.py"]
