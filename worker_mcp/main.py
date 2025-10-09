from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"service": "worker_mcp", "status": "running"}
