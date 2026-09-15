import os
from functools import lru_cache


class Settings:
    """Central app configuration.

    Values can be overridden via environment variables so the same code
    works locally, in Docker, and in CI without edits.
    """

    APP_NAME: str = "OpenReframe"
    APP_VERSION: str = "0.1.0"

    # --- Storage paths -----------------------------------------------
    UPLOAD_DIR: str = os.getenv("OPENREFRAME_UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OPENREFRAME_OUTPUT_DIR", "outputs")

    # --- Media validation ----------------------------------------------
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

    # --- YOLO -----------------------------------------------------------
    # Any ultralytics-compatible weights file/name. "yolov8n.pt" is the
    # smallest/fastest checkpoint and is downloaded automatically by
    # ultralytics on first use if not already present locally.
    YOLO_MODEL: str = os.getenv("OPENREFRAME_YOLO_MODEL", "yolov8n.pt")
    YOLO_CONFIDENCE: float = float(os.getenv("OPENREFRAME_YOLO_CONF", "0.35"))
    # Classes ultralytics/COCO considers "subjects" worth framing on.
    # person, cat, dog by default -- extend as needed.
    YOLO_PRIORITY_CLASSES = ("person", "cat", "dog")

    # --- Batch image reframing --------------------------------------------
    # Upper bound on how many files a single /image/reframe-batch request
    # can enqueue at once, mostly to keep one request from saving an
    # unbounded number of files to disk before the job even starts.
    MAX_BATCH_FILES: int = int(os.getenv("OPENREFRAME_MAX_BATCH_FILES", "300"))

    # --- Video pipeline ---------------------------------------------------
    # Run detection every N frames and interpolate/smooth in between,
    # instead of running YOLO on every single frame (much faster).
    VIDEO_DETECTION_STRIDE: int = int(os.getenv("OPENREFRAME_VIDEO_STRIDE", "5"))
    # Exponential smoothing factor for the tracked subject center
    # (0 = no movement, 1 = no smoothing / instant jump).
    VIDEO_SMOOTHING_ALPHA: float = float(os.getenv("OPENREFRAME_SMOOTHING_ALPHA", "0.25"))

    # --- Redis / RQ ------------------------------------------------------
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    RQ_QUEUE_NAME: str = os.getenv("OPENREFRAME_QUEUE", "openreframe")
    JOB_TIMEOUT_SECONDS: int = int(os.getenv("OPENREFRAME_JOB_TIMEOUT", "1800"))

    def ensure_dirs(self) -> None:
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
