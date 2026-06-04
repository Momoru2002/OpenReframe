from fastapi import FastAPI
from app.api.images import router as image_router
from app.api.videos import router as video_router

app = FastAPI(
    title="OpenReframe",
    version="0.1.0"
)

app.include_router(video_router)
app.include_router(image_router)


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