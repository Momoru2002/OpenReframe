"""Video reframing: YOLO-tracked subject position -> per-frame smart
crop -> ffmpeg mux (so the original audio track is preserved).

Pipeline:
  1. Read the video frame-by-frame with OpenCV.
  2. Run YOLO every `VIDEO_DETECTION_STRIDE` frames (full detection on
     every frame would be slow); reuse/interpolate the last known
     subject center for frames in between.
  3. Exponentially smooth the tracked center so the crop window pans
     instead of jittering frame to frame.
  4. Crop each frame to the target aspect ratio around the smoothed
     center and write a video-only output with OpenCV's VideoWriter.
  5. Shell out to ffmpeg to mux the original audio track back onto the
     cropped video (and re-encode to a widely compatible codec).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np

from app.core.config import get_settings
from app.services.image_reframe import _crop_box_for_center, parse_ratio
from app.services.yolo_tracker import detect_subject

settings = get_settings()

ProgressCallback = Optional[Callable[[int, int], None]]


@dataclass
class VideoReframeResult:
    output_path: str
    frame_count: int
    fps: float
    width: int
    height: int


def _has_audio_stream(path: str) -> bool:
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=index", "-of", "csv=p=0", path,
        ],
        capture_output=True, text=True,
    )
    return probe.returncode == 0 and probe.stdout.strip() != ""


def _mux_audio(video_only_path: str, source_path: str, final_path: str) -> None:
    """Combine the reframed (silent) video with the source's audio
    track. Falls back to a plain re-encode/copy if there's no audio."""
    if _has_audio_stream(source_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", video_only_path,
            "-i", source_path,
            "-map", "0:v:0", "-map", "1:a:0?",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            final_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_only_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            final_path,
        ]
    subprocess.run(cmd, check=True, capture_output=True)


def reframe_video(
    input_path: str,
    output_path: str,
    ratio: str = "9:16",
    use_yolo: bool = True,
    on_progress: ProgressCallback = None,
) -> VideoReframeResult:
    """Reframe a video file to `ratio`, tracking the main subject with
    YOLO so the crop window follows them across frames."""
    target_ratio = parse_ratio(ratio)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Figure out the output crop size once, from the source dimensions.
    crop_x1, crop_y1, crop_x2, crop_y2 = _crop_box_for_center(
        src_w, src_h, target_ratio, src_w / 2, src_h / 2
    )
    out_w, out_h = crop_x2 - crop_x1, crop_y2 - crop_y1

    silent_path = output_path + ".silent.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(silent_path, fourcc, fps, (out_w, out_h))

    smoothed_center: Optional[tuple[float, float]] = None
    alpha = settings.VIDEO_SMOOTHING_ALPHA
    frame_idx = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            raw_center = None
            if use_yolo and frame_idx % settings.VIDEO_DETECTION_STRIDE == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                subject = detect_subject(rgb)
                if subject is not None:
                    raw_center = subject.center

            if raw_center is not None:
                if smoothed_center is None:
                    smoothed_center = raw_center
                else:
                    smoothed_center = (
                        alpha * raw_center[0] + (1 - alpha) * smoothed_center[0],
                        alpha * raw_center[1] + (1 - alpha) * smoothed_center[1],
                    )
            elif smoothed_center is None:
                smoothed_center = (src_w / 2, src_h / 2)
            # else: no new detection this frame -> keep last smoothed
            # center (subject assumed roughly stationary between samples).

            x1, y1, x2, y2 = _crop_box_for_center(
                src_w, src_h, target_ratio, *smoothed_center
            )
            cropped = frame[y1:y2, x1:x2]
            if cropped.shape[1] != out_w or cropped.shape[0] != out_h:
                cropped = cv2.resize(cropped, (out_w, out_h))

            writer.write(cropped)
            frame_idx += 1

            if on_progress and total_frames:
                on_progress(frame_idx, total_frames)
    finally:
        cap.release()
        writer.release()

    _mux_audio(silent_path, input_path, output_path)

    return VideoReframeResult(
        output_path=output_path,
        frame_count=frame_idx,
        fps=fps,
        width=out_w,
        height=out_h,
    )
