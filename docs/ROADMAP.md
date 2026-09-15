# Roadmap

## Done
- [x] FastAPI backend scaffolding + CI
- [x] Next.js frontend scaffolding + CI
- [x] `image_reframe.py` — ratio parsing + subject-aware crop-box math
- [x] `yolo_tracker.py` — YOLO subject detection, priority-class
      selection (person/cat/dog), area-based fallback
- [x] `/image/reframe` endpoint (synchronous smart crop)
- [x] `video_reframe.py` — OpenCV + YOLO tracking pipeline with
      exponential smoothing, ffmpeg audio muxing
- [x] `/video/reframe` + `/video/status/{job_id}` — async pipeline via
      Redis/RQ
- [x] `docker-compose.yml` — redis, api, worker, frontend, nginx
- [x] Frontend upload/preview UI wired to the real API
- [x] Backend test suite (pytest, YOLO mocked out for speed/no-GPU CI)
- [x] Batch image reframing (`/image/reframe-batch` + `/image/batch-status/{job_id}`) —
      up to `MAX_BATCH_FILES` images per request, processed as one background
      job so hundreds of photos don't block the API or time out
- [x] Frontend: multi-file image upload with batch job polling + results grid
- [x] Frontend: video upload tab with job-status polling and before/after preview

## Next up
- [ ] **SAM (Segment Anything)** integration for pixel-accurate subject
      masks instead of a bounding box — would improve crop framing for
      irregularly-shaped or partially-occluded subjects.
- [ ] **Outpainting** to fill in extended canvas when the target ratio
      is wider/taller than any valid crop of the source (currently we
      always crop; there's no generative fill fallback yet).
- [ ] **Multi-subject framing** — when there are two+ important
      subjects (e.g. an interview with two speakers), keep both in
      frame instead of picking just one.
- [ ] Persist job/media metadata in a real datastore instead of just
      the filesystem + Redis job results (useful once this needs to
      run multi-user).
- [ ] Per-item progress for batch jobs (currently only queued/started/
      finished — no "X of N done" while a batch is running).
