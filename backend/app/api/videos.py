from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

import os

from app.services.video_reframe import (
    get_video_metadata
)

router = APIRouter(
    prefix="/video",
    tags=["Videos"]
)

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)

ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv"
}


def validate_video(filename: str):

    ext = os.path.splitext(
        filename
    )[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only video files are allowed"
        )


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...)
):

    validate_video(
        file.filename
    )

    filepath = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    with open(filepath, "wb") as buffer:
        buffer.write(
            await file.read()
        )

    size_mb = round(
        os.path.getsize(filepath)
        / (1024 * 1024),
        2
    )

    metadata = get_video_metadata(
        filepath
    )

    return {
        "success": True,
        "filename": file.filename,
        "saved_to": filepath,
        "size_mb": size_mb,
        "metadata": metadata
    }