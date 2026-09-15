import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.yolo_tracker import BoundingBox

client = TestClient(app)


def _fake_image_bytes(w=400, h=300, color=(10, 20, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="JPEG")
    buf.seek(0)
    return buf.read()


def test_upload_image():
    files = {"file": ("test.jpg", _fake_image_bytes(400, 300), "image/jpeg")}
    resp = client.post("/image/upload", files=files)
    assert resp.status_code == 200
    body = resp.json()
    assert body["orientation"] == "landscape"
    assert body["width"] == 400


def test_reframe_rejects_bad_extension():
    files = {"file": ("test.txt", b"not an image", "text/plain")}
    resp = client.post("/image/reframe", files=files, data={"ratio": "9:16"})
    assert resp.status_code == 400


def test_reframe_without_yolo_uses_center_crop():
    files = {"file": ("test.jpg", _fake_image_bytes(1000, 1000), "image/jpeg")}
    resp = client.post(
        "/image/reframe", files=files, data={"ratio": "9:16", "use_yolo": "false"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["subject_detected"] is False


def test_reframe_with_mocked_yolo_subject(monkeypatch):
    fake_subject = BoundingBox(x1=800, y1=800, x2=900, y2=900, confidence=0.88, label="person")
    monkeypatch.setattr(
        "app.services.image_reframe.detect_subject", lambda frame: fake_subject
    )

    files = {"file": ("test.jpg", _fake_image_bytes(1000, 1000), "image/jpeg")}
    resp = client.post(
        "/image/reframe", files=files, data={"ratio": "1:1", "use_yolo": "true"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["subject_detected"] is True
    assert body["subject"]["label"] == "person"


def test_list_ratios():
    resp = client.get("/image/ratios")
    assert resp.status_code == 200
    assert "9:16" in resp.json()["presets"]


class _FakeJob:
    id = "fake-job-123"

    def get_status(self):
        return "queued"


def test_reframe_batch_enqueues_job(monkeypatch):
    monkeypatch.setattr(
        "app.api.images.enqueue_batch_reframe",
        lambda **kwargs: _FakeJob(),
    )

    files = [
        ("files", ("a.jpg", _fake_image_bytes(200, 200), "image/jpeg")),
        ("files", ("b.jpg", _fake_image_bytes(200, 200), "image/jpeg")),
    ]
    resp = client.post("/image/reframe-batch", files=files, data={"ratio": "1:1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "fake-job-123"
    assert body["file_count"] == 2


def test_reframe_batch_rejects_empty():
    resp = client.post("/image/reframe-batch", files=[], data={"ratio": "1:1"})
    assert resp.status_code in (400, 422)


def test_reframe_batch_rejects_bad_extension(monkeypatch):
    monkeypatch.setattr(
        "app.api.images.enqueue_batch_reframe",
        lambda **kwargs: _FakeJob(),
    )
    files = [("files", ("a.txt", b"not an image", "text/plain"))]
    resp = client.post("/image/reframe-batch", files=files, data={"ratio": "1:1"})
    assert resp.status_code == 400


def test_reframe_batch_too_many_files(monkeypatch):
    monkeypatch.setattr("app.api.images.settings.MAX_BATCH_FILES", 1)
    files = [
        ("files", ("a.jpg", _fake_image_bytes(50, 50), "image/jpeg")),
        ("files", ("b.jpg", _fake_image_bytes(50, 50), "image/jpeg")),
    ]
    resp = client.post("/image/reframe-batch", files=files, data={"ratio": "1:1"})
    assert resp.status_code == 400


def test_batch_status_finished(monkeypatch):
    class _FinishedJob:
        def get_status(self):
            return "finished"

        result = [
            {"success": True, "source_filename": "a.jpg", "filename": "reframed_a.jpg"},
            {"success": False, "source_filename": "b.jpg", "error": "boom"},
        ]

    monkeypatch.setattr("app.api.images.Job.fetch", lambda job_id, connection: _FinishedJob())

    resp = client.get("/image/batch-status/fake-job-123")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "finished"
    assert body["succeeded"] == 1
    assert body["failed"] == 1


def test_batch_status_not_found(monkeypatch):
    def _raise(job_id, connection):
        raise Exception("no such job")

    monkeypatch.setattr("app.api.images.Job.fetch", _raise)

    resp = client.get("/image/batch-status/does-not-exist")
    assert resp.status_code == 404
