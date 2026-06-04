from fastapi.responses import FileResponse

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from PIL import Image
import os

from app.services.image_reframe import (
    portrait_to_landscape
)

router = APIRouter(
    prefix="/image",
    tags=["Images"]
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp"
}


def validate_image(filename: str):
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only image files are allowed"
        )


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...)
):
    validate_image(file.filename)

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


@router.post("/portrait-to-landscape")
async def convert_portrait(
    file: UploadFile = File(...)
):
    validate_image(file.filename)

    filepath = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(filepath, "wb") as buffer:
        buffer.write(
            await file.read()
        )

    image = Image.open(filepath)

    result = portrait_to_landscape(image)

    output_filename = (
        f"landscape_{file.filename}"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_filename
    )

    result.save(output_path)

    return {
        "success": True,
        "saved_to": output_path,
        "filename": output_filename,
        "width": result.width,
        "height": result.height
    }

@router.get("/download/{filename}")
async def download_file(filename: str):

    file_path = os.path.join(
        OUTPUT_DIR,
        filename
    )

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )