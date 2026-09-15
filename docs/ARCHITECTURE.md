# Architecture

```text
┌────────────┐      ┌────────────┐      ┌──────────────┐      ┌───────────┐
│  Frontend   │─────▶│  API        │─────▶│  Workers      │─────▶│  Storage   │
│  (Next.js)  │      │  (FastAPI)  │      │  (Redis + RQ) │      │            │
└────────────┘      └────────────┘      └──────────────┘      └───────────┘
```

## Components

### Frontend (Next.js, `frontend/`)
- `app/page.tsx` renders the `Uploader` component.
- `components/Uploader.tsx` handles file selection, ratio choice, the
  YOLO on/off toggle, and calling the API — then shows the original
  and reframed images side by side.
- `lib/api.ts` is the thin fetch wrapper (`reframeImage`, `resultUrl`,
  `listRatios`), reading the API base URL from `NEXT_PUBLIC_API_URL`.

### API (FastAPI, `backend/app/`)
- `api/images.py` — `/image/upload` and `/image/reframe` are
  synchronous (fast enough to run inline). `/image/reframe-batch`
  is async: it saves all uploaded files to a per-batch folder and
  enqueues one RQ job that reframes them sequentially, returning a
  `job_id` polled via `/image/batch-status/{job_id}` — same pattern
  as video, used so a request with e.g. 200 photos doesn't block the
  API or hit an HTTP timeout. A failure on one file doesn't stop the
  rest of the batch.
- `api/videos.py` — video reframing is too slow to run inline, so
  `/video/reframe` enqueues a job on the RQ queue and returns a
  `job_id`; the client polls `/video/status/{job_id}`.
- `core/config.py` — a single `Settings` object (env-var driven) for
  storage paths, YOLO model/confidence, video sampling stride and
  smoothing, and Redis connection info.

### Services (`backend/app/services/`)
- `yolo_tracker.py` — lazily loads an Ultralytics YOLO model and
  exposes `detect_subject(frame) -> BoundingBox | None`. Priority
  goes to "subject" classes (person/cat/dog), falling back to the
  largest detected box. Lazy import keeps torch off the path for
  anything that doesn't need it.
- `image_reframe.py` — ratio parsing (`"9:16"`, `"1:1"`, custom
  `"W:H"`), the crop-box math (`_crop_box_for_center`, clamped to
  image bounds), and `reframe_image()` which ties YOLO detection to
  the crop.
- `video_reframe.py` — reads a video frame-by-frame with OpenCV, runs
  YOLO every `VIDEO_DETECTION_STRIDE` frames (not every frame, for
  speed), exponentially smooths the tracked center so the crop pans
  instead of jittering, writes the cropped (silent) video, then shells
  out to `ffmpeg` to mux the original audio track back in.

### Workers (`backend/app/workers/queue.py`)
- Defines the Redis connection and RQ `Queue` (a single queue handles
  both video and batch-image jobs).
- `process_video_reframe_job` / `process_batch_reframe_job` are the
  picklable job functions RQ actually runs; `enqueue_video_reframe` /
  `enqueue_batch_reframe` are what the API calls to queue them.
- `python -m app.workers.queue` starts a worker process that consumes
  the queue.

### Infra
- `infra/nginx/nginx.conf` reverse-proxies `/` to the frontend and
  `/api/` to the backend (stripping the `/api` prefix).
- `docker-compose.yml` wires up `redis`, `api`, `worker`, `frontend`,
  and `nginx` with a shared `media-data` volume so the API and worker
  see the same uploaded/output files.

## Data flow: image reframe (synchronous)
1. Frontend uploads the file + target ratio to `POST /image/reframe`.
2. The API saves the upload, runs YOLO (if enabled) to find the
   subject, computes the crop box, saves the result.
3. The response includes the output filename and detected subject
   info; the frontend fetches the image from `GET /image/result/{filename}`.

## Data flow: video reframe (asynchronous)
1. Frontend uploads the file to `POST /video/reframe`; the API saves
   it and enqueues a job, returning a `job_id`.
2. A worker process picks up the job, runs the full frame-by-frame
   pipeline, and writes the output.
3. The frontend (or any client) polls `GET /video/status/{job_id}`
   until `status == "finished"`, then fetches the result.

## Data flow: batch image reframe (asynchronous)
1. Frontend uploads N files to `POST /image/reframe-batch`; the API
   saves them to a unique batch folder and enqueues one job covering
   all of them, returning a `job_id`.
2. A worker process reframes each image in order, saving successful
   outputs and recording an error message (without stopping the
   batch) for any file that fails.
3. The frontend polls `GET /image/batch-status/{job_id}`; once
   `status == "finished"`, the response includes a per-file results
   array plus `succeeded`/`failed` counts.
