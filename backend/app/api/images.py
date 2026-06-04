from fastapi import APIRouter, UploadFile, File
from PIL import Image
import os

router = APIRouter(
    prefix="/image",
    tags=["Images"]
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    filepath = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(filepath, "wb") as buffer:
        buffer.write(
            await file.read()
        )

    image = Image.open(filepath)

    orientation = (
        "portrait"
        if image.height > image.width
        else "landscape"
    )

    return {
        "filename": file.filename,
        "width": image.width,
        "height": image.height,
        "orientation": orientation
    }