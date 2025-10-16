FROM python:3.10-slim

WORKDIR /app

# 🔹 Instalar dependencias nativas para soporte Snappy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libsnappy-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
