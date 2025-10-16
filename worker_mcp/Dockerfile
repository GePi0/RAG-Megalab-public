# worker_mcp/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Uvicorn corre en modo host, no exponer puertos Docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
