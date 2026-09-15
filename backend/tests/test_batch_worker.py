"""Tests for the batch image-reframe job body that runs inside the RQ
worker process. YOLO is never touched here (use_yolo=False), keeping
this fast and dependency-free."""
import os

from PIL import Image

from app.workers.queue import process_batch_reframe_job


def test_process_batch_reframe_job_all_succeed(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    paths = []
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        p = input_dir / name
        Image.new("RGB", (400, 300), (10, 20, 30)).save(p)
        paths.append(str(p))

    results = process_batch_reframe_job(
        input_paths=paths, output_dir=str(output_dir), ratio="1:1", use_yolo=False
    )

    assert len(results) == 3
    assert all(r["success"] for r in results)
    for r in results:
        assert os.path.isfile(os.path.join(str(output_dir), r["filename"]))
        assert r["subject_detected"] is False


def test_process_batch_reframe_job_continues_after_one_failure(tmp_path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    good_path = input_dir / "good.jpg"
    Image.new("RGB", (300, 300), (1, 2, 3)).save(good_path)

    bad_path = input_dir / "bad.jpg"
    bad_path.write_bytes(b"not actually an image")

    results = process_batch_reframe_job(
        input_paths=[str(good_path), str(bad_path)],
        output_dir=str(output_dir),
        ratio="9:16",
        use_yolo=False,
    )

    assert len(results) == 2
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert "error" in results[1]
