import os

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from rq.job import Job

from app.core.config import get_settings
from app.workers.queue import enqueue_video_reframe, redis_conn

settings = get_settings()

router = APIRouter(prefix="/video", tags=["Videos"])


def validate_video(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Only {', '.join(sorted(settings.ALLOWED_VIDEO_EXTENSIONS))} files are allowed",
        )


@router.post("/reframe")
async def reframe_video_endpoint(
    file: UploadFile = File(...),
    ratio: str = Form("9:16"),
    use_yolo: bool = Form(True),
):
    """Upload a video and enqueue an async job that tracks the subject
    with YOLO and reframes every frame to `ratio`. Video reframing is
    too slow to do inline in a request, so this returns a job id you
    poll via GET /video/status/{job_id}."""
    validate_video(file.filename)

    input_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(input_path, "wb") as buffer:
        buffer.write(await file.read())

    safe_ratio = ratio.replace(":", "x")
    output_filename = f"reframed_{safe_ratio}_{file.filename}"
    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)

    job = enqueue_video_reframe(
        input_path=input_path,
        output_path=output_path,
        ratio=ratio,
        use_yolo=use_yolo,
    )

    return {
        "job_id": job.id,
        "status": job.get_status(),
        "output_filename": output_filename,
    }


@router.get("/status/{job_id}")
def job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception as exc:  # rq raises NoSuchJobError
        raise HTTPException(status_code=404, detail="Job not found") from exc

    status = job.get_status()
    response = {"job_id": job_id, "status": status}

    if status == "finished":
        response["result"] = job.result
    elif status == "failed":
        response["error"] = str(job.exc_info)

    return response


@router.get("/result/{filename}")
def get_result(filename: str):
    path = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
