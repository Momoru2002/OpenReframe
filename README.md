<h1 align="center">🎬 OpenReframe</h1>

<p align="center">
  <b>Production-oriented, open-source media reframing platform</b>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=600&size=18&duration=3000&pause=900&color=3B82F6&center=true&vCenter=true&width=750&lines=Smart%2C+subject-aware+reframing+for+images+%26+video.;FastAPI+%2B+Next.js+%2B+background+workers.;YOLO-based+subject+tracking+(in+progress).;Open+for+contributions."/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Early%20Development-yellow?style=flat-square">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3B82F6?style=flat-square&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/FastAPI-Backend-3B82F6?style=flat-square&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/Next.js-Frontend-3B82F6?style=flat-square&logo=nextdotjs&logoColor=white">
  <img src="https://img.shields.io/badge/License-MIT-3B82F6?style=flat-square">
</p>

<br>

## About

**OpenReframe** is an open-source platform for automatically reframing images and video into different aspect ratios (e.g. landscape → vertical/square) while keeping the important subject in frame — the kind of "smart crop" used to repurpose long-form video into social clips, or adapt a single image for multiple placements.

The project is designed around a clean separation of concerns: a **FastAPI** backend exposes reframing endpoints, heavy processing (video/image transforms, subject tracking) runs on **background workers** (Redis + RQ) instead of blocking requests, and a **Next.js** frontend provides the upload/preview UI.

> 🚧 **Status: early development.** The architecture and CI scaffolding are in place; the core reframing logic (YOLO-based subject tracking, video pipeline) is actively being built. See [Roadmap](#roadmap) below.

<br>

## Architecture

```text
┌────────────┐      ┌────────────┐      ┌──────────────┐      ┌───────────┐
│  Frontend   │─────▶│  API        │─────▶│  Workers      │─────▶│  Storage   │
│  (Next.js)  │      │  (FastAPI)  │      │  (Redis + RQ) │      │            │
└────────────┘      └────────────┘      └──────────────┘      └───────────┘
```

- **Frontend** — Next.js app for uploading media and previewing reframed output
- **API** — FastAPI service that accepts image/video reframe requests and enqueues jobs
- **Workers** — RQ workers that run the actual reframing pipeline (OpenCV / Pillow / ffmpeg) asynchronously
- **Storage** — processed media output (local/object storage, pluggable)

<br>

## Features

**Planned / in progress:**
- 🎯 Subject-aware reframing driven by object detection (YOLO)
- 🖼️ Image reframing service (Pillow/OpenCV based crop & resize)
- 🎞️ Video reframing service (ffmpeg-based pipeline with per-frame tracking)
- ⚙️ Async job processing via Redis/RQ so uploads don't block the API
- 🌐 Minimal web UI for uploading media and previewing results
- 🔁 CI pipelines for backend and frontend (GitHub Actions)

**On the roadmap:**
- YOLO-based subject detection & tracking
- SAM (Segment Anything Model) for precise subject masks
- Outpainting to fill extended canvas when reframing to a wider/taller ratio

<br>

## Tech Stack

<img src="https://skillicons.dev/icons?i=python,fastapi,opencv,nextjs,ts,redis,docker,nginx"/>

`FastAPI` `Uvicorn` `Pillow` `OpenCV` `Redis` `RQ` `Next.js` `TypeScript` `Nginx` `Docker`

<br>

## Project Structure

```text
OpenReframe/
├── backend/
│   ├── app/
│   │   ├── api/            # images.py, videos.py — FastAPI routers
│   │   ├── core/           # config.py — app settings
│   │   ├── services/       # image_reframe.py, video_reframe.py, yolo_tracker.py
│   │   ├── workers/        # queue.py — RQ worker entrypoint
│   │   └── main.py         # FastAPI app entrypoint
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Uploader.tsx, etc.
│   └── lib/                 # api.ts — API client config
├── infra/
│   └── nginx/                # reverse proxy config
├── docs/
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── .github/workflows/        # backend-ci, frontend-ci
├── docker-compose.yml
└── LICENSE
```

<br>

## Getting Started

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000`.

### Full stack (Docker)

```bash
docker-compose up --build
```

> `docker-compose.yml` and service configs are still being fleshed out — expect this to evolve as the workers/storage layer is implemented.

<br>

## Roadmap

- [ ] Wire up `images.py` / `videos.py` endpoints to their respective services
- [ ] Implement `image_reframe.py` (crop/resize with a fixed focal point)
- [ ] Implement `yolo_tracker.py` for subject detection & tracking
- [ ] Implement `video_reframe.py` (ffmpeg pipeline driven by tracked subject position)
- [ ] Integrate SAM for pixel-accurate subject masks
- [ ] Add outpainting for extending canvas on aspect-ratio mismatches
- [ ] Flesh out `docker-compose.yml` (API, worker, Redis, nginx services)
- [ ] Build out the frontend upload/preview flow beyond the current placeholder page

<br>

## Contributing

OpenReframe is early-stage and open to contributions — whether that's implementing a roadmap item above, improving CI, or just filing issues for the direction you'd like to see. Fork the repo, open a PR, and it'll get reviewed.

<br>

## License

Released under the [MIT License](./LICENSE).

<br>

<p align="center">
  <sub>Built by Muhammad Almas Albirra Hamid · Informatics Engineering, Universitas Muhammadiyah Riau</sub>
</p>
