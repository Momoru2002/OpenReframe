from app.services.yolo_tracker import BoundingBox, _select_main_subject


def _box(label, conf, area_side=50):
    return BoundingBox(x1=0, y1=0, x2=area_side, y2=area_side, confidence=conf, label=label)


def test_select_main_subject_prefers_priority_class():
    boxes = [
        _box("bicycle", 0.95, area_side=500),
        _box("person", 0.4),
    ]
    chosen = _select_main_subject(boxes)
    assert chosen.label == "person"


def test_select_main_subject_highest_confidence_among_priority():
    boxes = [
        _box("person", 0.5),
        _box("dog", 0.9),
        _box("cat", 0.7),
    ]
    chosen = _select_main_subject(boxes)
    assert chosen.label == "dog"


def test_select_main_subject_falls_back_to_largest_area():
    boxes = [
        _box("bicycle", 0.3, area_side=20),
        _box("car", 0.6, area_side=200),
    ]
    chosen = _select_main_subject(boxes)
    assert chosen.label == "car"


def test_select_main_subject_empty():
    assert _select_main_subject([]) is None
