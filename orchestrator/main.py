from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"service": "orchestrator", "status": "running"}
