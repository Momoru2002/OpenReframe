"""RQ (Redis Queue) setup: the connection/queue used to enqueue
video-reframe and batch image-reframe jobs from the API, and the
worker entrypoint that consumes them.

Run a worker with:
    python -m app.workers.queue
or:
    rq worker openreframe --url redis://localhost:6379/0
"""
from __future__ import annotations

import os

from PIL import Image
from redis import Redis
from rq import Queue, Worker

from app.core.config import get_settings
from app.services.image_reframe import reframe_image
from app.services.video_reframe import reframe_video

settings = get_settings()

redis_conn = Redis.from_url(settings.REDIS_URL)
video_queue = Queue(settings.RQ_QUEUE_NAME, connection=redis_conn)


def process_video_reframe_job(
    input_path: str,
    output_path: str,
    ratio: str = "9:16",
    use_yolo: bool = True,
) -> dict:
    """The actual job body executed by the RQ worker process. Kept as a
    plain function (not a closure/lambda) so it's importable/picklable
    by RQ."""
    result = reframe_video(
        input_path=input_path,
        output_path=output_path,
        ratio=ratio,
        use_yolo=use_yolo,
    )
    return {
        "output_path": result.output_path,
        "frame_count": result.frame_count,
        "fps": result.fps,
        "width": result.width,
        "height": result.height,
    }


def enqueue_video_reframe(
    input_path: str,
    output_path: str,
    ratio: str = "9:16",
    use_yolo: bool = True,
):
    return video_queue.enqueue(
        process_video_reframe_job,
        input_path=input_path,
        output_path=output_path,
        ratio=ratio,
        use_yolo=use_yolo,
        job_timeout=settings.JOB_TIMEOUT_SECONDS,
    )


def process_batch_reframe_job(
    input_paths: list[str],
    output_dir: str,
    ratio: str = "9:16",
    use_yolo: bool = True,
) -> list[dict]:
    """Job body for reframing many images in one background job. Runs
    sequentially (YOLO model stays loaded/cached across images once
    warmed up) and keeps going even if one file fails, so a single bad
    upload doesn't lose the whole batch.

    Returns one result dict per input file, in the same order, each
    with either the reframe output info or an "error" key.
    """
    results: list[dict] = []

    for input_path in input_paths:
        filename = os.path.basename(input_path)
        try:
            image = Image.open(input_path).convert("RGB")
            result, subject = reframe_image(image, ratio=ratio, use_yolo=use_yolo)

            safe_ratio = ratio.replace(":", "x")
            output_filename = f"reframed_{safe_ratio}_{filename}"
            output_path = os.path.join(output_dir, output_filename)
            result.save(output_path)

            results.append(
                {
                    "success": True,
                    "source_filename": filename,
                    "filename": output_filename,
                    "width": result.width,
                    "height": result.height,
                    "subject_detected": subject is not None,
                    "subject": (
                        {"label": subject.label, "confidence": subject.confidence}
                        if subject
                        else None
                    ),
                }
            )
        except Exception as exc:  # noqa: BLE001 - keep processing the rest of the batch
            results.append(
                {
                    "success": False,
                    "source_filename": filename,
                    "error": str(exc),
                }
            )

    return results


def enqueue_batch_reframe(
    input_paths: list[str],
    output_dir: str,
    ratio: str = "9:16",
    use_yolo: bool = True,
):
    return video_queue.enqueue(
        process_batch_reframe_job,
        input_paths=input_paths,
        output_dir=output_dir,
        ratio=ratio,
        use_yolo=use_yolo,
        job_timeout=settings.JOB_TIMEOUT_SECONDS,
    )


def run_worker() -> None:
    worker = Worker([video_queue], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run_worker()
