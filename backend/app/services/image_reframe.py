"""Image reframing: fixed letterbox conversion + YOLO-driven smart crop."""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image

from app.services.yolo_tracker import BoundingBox, detect_subject

# "16:9", "9:16", "1:1", "4:5" -> float ratio (width / height)
RATIO_PRESETS = {
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "1:1": 1.0,
    "4:5": 4 / 5,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
}


def parse_ratio(ratio: str) -> float:
    if ratio in RATIO_PRESETS:
        return RATIO_PRESETS[ratio]
    try:
        w, h = ratio.split(":")
        return float(w) / float(h)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(
            f"Invalid ratio '{ratio}'. Use a preset ({', '.join(RATIO_PRESETS)}) "
            "or 'W:H' notation, e.g. '9:16'."
        ) from exc


def portrait_to_landscape(image: Image.Image) -> Image.Image:
    """Legacy behaviour: pad a portrait image out to 16:9 with black
    bars (no subject awareness). Kept for backwards compatibility."""
    target_ratio = 16 / 9

    width = image.width
    height = image.height

    new_width = int(height * target_ratio)

    if new_width <= width:
        return image

    canvas = Image.new("RGB", (new_width, height), (0, 0, 0))
    offset_x = (new_width - width) // 2
    canvas.paste(image, (offset_x, 0))

    return canvas


def _crop_box_for_center(
    img_width: int,
    img_height: int,
    target_ratio: float,
    center_x: float,
    center_y: float,
) -> tuple[int, int, int, int]:
    """Compute the largest crop window at `target_ratio` that fits
    inside the image, centered as close as possible to (center_x,
    center_y) without spilling outside the image bounds."""
    current_ratio = img_width / img_height

    if current_ratio > target_ratio:
        # Image is relatively wider than target -> crop width.
        crop_h = img_height
        crop_w = int(crop_h * target_ratio)
    else:
        # Image is relatively taller than target -> crop height.
        crop_w = img_width
        crop_h = int(crop_w / target_ratio)

    x1 = int(center_x - crop_w / 2)
    y1 = int(center_y - crop_h / 2)

    # Clamp so the crop window stays fully inside the source image.
    x1 = max(0, min(x1, img_width - crop_w))
    y1 = max(0, min(y1, img_height - crop_h))

    return x1, y1, x1 + crop_w, y1 + crop_h


def subject_aware_crop(
    image: Image.Image,
    target_ratio: float,
    subject: Optional[BoundingBox] = None,
) -> Image.Image:
    """Crop `image` to `target_ratio`, centered on the detected subject
    when one is available, falling back to a plain center crop."""
    width, height = image.size

    if subject is not None:
        center_x, center_y = subject.center
    else:
        center_x, center_y = width / 2, height / 2

    box = _crop_box_for_center(width, height, target_ratio, center_x, center_y)
    return image.crop(box)


def reframe_image(
    image: Image.Image,
    ratio: str = "9:16",
    use_yolo: bool = True,
) -> tuple[Image.Image, Optional[BoundingBox]]:
    """Main entry point: reframe an image to `ratio`, using YOLO to find
    the subject to crop around when `use_yolo` is True. Returns the
    reframed image plus the detected subject box (or None), so callers
    can surface what the model saw.
    """
    target_ratio = parse_ratio(ratio)

    subject: Optional[BoundingBox] = None
    if use_yolo:
        frame = np.array(image.convert("RGB"))
        subject = detect_subject(frame)

    result = subject_aware_crop(image, target_ratio, subject)
    return result, subject
