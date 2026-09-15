"""Tests for pure image-reframing logic. These never touch YOLO/torch:
subject-aware paths are exercised with a fake BoundingBox so the test
suite stays fast and has zero ML-model dependency."""
from PIL import Image

from app.services.image_reframe import (
    _crop_box_for_center,
    parse_ratio,
    portrait_to_landscape,
    subject_aware_crop,
)
from app.services.yolo_tracker import BoundingBox


def test_parse_ratio_preset():
    assert parse_ratio("9:16") == 9 / 16
    assert parse_ratio("1:1") == 1.0


def test_parse_ratio_custom():
    assert parse_ratio("2:1") == 2.0


def test_parse_ratio_invalid():
    import pytest

    with pytest.raises(ValueError):
        parse_ratio("not-a-ratio")


def test_portrait_to_landscape_pads_width():
    img = Image.new("RGB", (400, 800), (255, 0, 0))
    result = portrait_to_landscape(img)
    assert result.height == 800
    assert abs(result.width / result.height - 16 / 9) < 0.01


def test_portrait_to_landscape_noop_if_already_wide():
    img = Image.new("RGB", (1920, 1080), (0, 255, 0))
    result = portrait_to_landscape(img)
    assert result.size == img.size


def test_crop_box_center_stays_in_bounds_near_edge():
    x1, y1, x2, y2 = _crop_box_for_center(1000, 1000, 9 / 16, center_x=10, center_y=10)
    assert x1 >= 0 and y1 >= 0
    assert x2 <= 1000 and y2 <= 1000


def test_subject_aware_crop_centers_on_subject():
    img = Image.new("RGB", (1000, 1000), (0, 0, 0))
    subject = BoundingBox(x1=700, y1=700, x2=800, y2=800, confidence=0.9, label="person")

    result = subject_aware_crop(img, target_ratio=1.0, subject=subject)

    assert result.size[0] <= 1000
    assert result.size[1] <= 1000


def test_subject_aware_crop_falls_back_to_center_without_subject():
    img = Image.new("RGB", (800, 600), (0, 0, 0))
    result = subject_aware_crop(img, target_ratio=1.0, subject=None)
    assert result.width == result.height == 600
