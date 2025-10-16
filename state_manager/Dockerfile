# ------------------------------------------------------------
# 🤖 State Manager + Cognitive Memory API (FASE 8.1)
# ------------------------------------------------------------
FROM python:3.10-slim

WORKDIR /app

# Copiamos e instalamos dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . .

# Exponemos puerto de la API cognitiva
EXPOSE 8010

# Ambiente básico
ENV PYTHONUNBUFFERED=1

# Ejecutamos el consumidor + API FastAPI juntos
CMD bash -c "python main.py & uvicorn api_memory:app --host 0.0.0.0 --port 8010"
