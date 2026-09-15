"""Subject detection/tracking powered by YOLO (Ultralytics).

This module keeps the heavy ML dependency isolated behind a small,
easy-to-mock interface (`detect_subject`) so the rest of the app
(image/video reframing, tests) never has to touch the model directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Sequence

import numpy as np

from app.core.config import get_settings

settings = get_settings()


@dataclass
class BoundingBox:
    """Axis-aligned box in absolute pixel coordinates, top-left origin."""

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    label: str

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2

    @property
    def area(self) -> float:
        return max(0.0, self.width) * max(0.0, self.height)


@lru_cache
def _load_model():
    """Lazily import & load the YOLO model.

    Deferred import keeps `ultralytics`/`torch` off the hot path for
    code paths that never need it (e.g. plain letterbox reframing),
    and means the whole app doesn't fail to start if the ML deps
    aren't installed yet in a given environment.
    """
    from ultralytics import YOLO

    return YOLO(settings.YOLO_MODEL)


def _select_main_subject(boxes: Sequence[BoundingBox]) -> Optional[BoundingBox]:
    """Pick the single most relevant detection to frame the shot on.

    Priority: known "subject" classes (person/cat/dog...) ranked by
    confidence, falling back to the largest-area detection of anything
    else so a reframe still has *something* to anchor on.
    """
    if not boxes:
        return None

    priority = [b for b in boxes if b.label in settings.YOLO_PRIORITY_CLASSES]
    if priority:
        return max(priority, key=lambda b: b.confidence)

    return max(boxes, key=lambda b: b.area)


def detect_boxes(frame: np.ndarray) -> list[BoundingBox]:
    """Run YOLO on a single BGR/RGB frame (numpy array) and return all
    detections above the configured confidence threshold."""
    model = _load_model()
    results = model.predict(
        frame,
        conf=settings.YOLO_CONFIDENCE,
        verbose=False,
    )

    boxes: list[BoundingBox] = []
    for result in results:
        names = result.names
        for box in result.boxes:
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            boxes.append(
                BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                    label=names.get(cls_id, str(cls_id)),
                )
            )
    return boxes


def detect_subject(frame: np.ndarray) -> Optional[BoundingBox]:
    """Detect the main subject in a single frame, or None if nothing
    matches the confidence threshold."""
    return _select_main_subject(detect_boxes(frame))
