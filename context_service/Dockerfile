FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CHROMA_DB_PATH=/app/chroma
ENV CHROMA_COLLECTION=rag_contexts
ENV EMBEDDING_MODEL=nomic-embed-text

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
