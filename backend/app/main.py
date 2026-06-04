from fastapi import FastAPI

app = FastAPI(
    title="OpenReframe",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "message": "Welcome to OpenReframe"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }