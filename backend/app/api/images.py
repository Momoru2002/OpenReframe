import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from rq.job import Job

from app.core.config import get_settings
from app.services.image_reframe import RATIO_PRESETS, portrait_to_landscape, reframe_image
from app.workers.queue import enqueue_batch_reframe, redis_conn

settings = get_settings()

router = APIRouter(prefix="/image", tags=["Images"])


def validate_image(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(sorted(settings.ALLOWED_IMAGE_EXTENSIONS))} files are allowed",
        )


async def _save_upload(file: UploadFile) -> str:
    validate_image(file.filename)
    filepath = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    return filepath


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    filepath = await _save_upload(file)
    image = Image.open(filepath)

    orientation = "portrait" if image.height > image.width else "landscape"

    return {
        "filename": file.filename,
        "width": image.width,
        "height": image.height,
        "orientation": orientation,
    }


@router.post("/portrait-to-landscape")
async def convert_portrait(file: UploadFile = File(...)):
    """Legacy letterbox conversion (no subject awareness)."""
    filepath = await _save_upload(file)
    image = Image.open(filepath)
    result = portrait_to_landscape(image)

    output_filename = f"landscape_{file.filename}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    result.save(output_path)

    return {
        "success": True,
        "saved_to": output_path,
        "filename": output_filename,
        "width": result.width,
        "height": result.height,
    }


@router.post("/reframe")
async def reframe(
    file: UploadFile = File(...),
    ratio: str = Form("9:16"),
    use_yolo: bool = Form(True),
):
    """Subject-aware smart crop: detects the main subject with YOLO
    (when use_yolo=True) and crops to `ratio` centered on it."""
    filepath = await _save_upload(file)
    image = Image.open(filepath).convert("RGB")

    try:
        result, subject = reframe_image(image, ratio=ratio, use_yolo=use_yolo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_ratio = ratio.replace(":", "x")
    output_filename = f"reframed_{safe_ratio}_{file.filename}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    result.save(output_path)

    return {
        "success": True,
        "filename": output_filename,
        "saved_to": output_path,
        "width": result.width,
        "height": result.height,
        "ratio": ratio,
        "subject_detected": subject is not None,
        "subject": (
            {
                "label": subject.label,
                "confidence": subject.confidence,
                "box": [subject.x1, subject.y1, subject.x2, subject.y2],
            }
            if subject
            else None
        ),
    }


@router.post("/reframe-batch")
async def reframe_batch(
    files: list[UploadFile] = File(...),
    ratio: str = Form("9:16"),
    use_yolo: bool = Form(True),
):
    """Reframe many images (e.g. up to a few hundred) in one go.

    Processing many images with YOLO can take a while, so this doesn't
    reframe inline like /image/reframe — it saves the uploads, enqueues
    a background job, and returns a job_id you poll via
    GET /image/batch-status/{job_id}, same pattern as video reframing.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > settings.MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: max is {settings.MAX_BATCH_FILES} per batch",
        )

    for f in files:
        validate_image(f.filename)

    # Give each batch its own upload subfolder so identically-named
    # files from different batches (or duplicate names within one
    # batch) never collide on disk.
    batch_dir = os.path.join(settings.UPLOAD_DIR, f"batch_{uuid.uuid4().hex[:12]}")
    os.makedirs(batch_dir, exist_ok=True)

    saved_paths = []
    for f in files:
        path = os.path.join(batch_dir, f.filename)
        with open(path, "wb") as buffer:
            buffer.write(await f.read())
        saved_paths.append(path)

    job = enqueue_batch_reframe(
        input_paths=saved_paths,
        output_dir=settings.OUTPUT_DIR,
        ratio=ratio,
        use_yolo=use_yolo,
    )

    return {
        "job_id": job.id,
        "status": job.get_status(),
        "file_count": len(saved_paths),
    }


@router.get("/batch-status/{job_id}")
def batch_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as exc:  # rq raises NoSuchJobError
        raise HTTPException(status_code=404, detail="Job not found") from exc

    status = job.get_status()
    response = {"job_id": job_id, "status": status}

    if status == "finished":
        results = job.result or []
        response["results"] = results
        response["succeeded"] = sum(1 for r in results if r.get("success"))
        response["failed"] = sum(1 for r in results if not r.get("success"))
    elif status == "failed":
        response["error"] = str(job.exc_info)

    return response


@router.get("/ratios")
def list_ratios():
    return {"presets": list(RATIO_PRESETS.keys())}


@router.get("/result/{filename}")
def get_result(filename: str):
    path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
