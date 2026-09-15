"use client";

import { useState } from "react";
import {
  reframeVideo,
  pollVideoStatus,
  videoResultUrl,
  VideoStatusResponse,
} from "@/lib/api";

const RATIOS = ["9:16", "1:1", "4:5", "16:9", "4:3"];

export default function VideoUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [ratio, setRatio] = useState("9:16");
  const [useYolo, setUseYolo] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<VideoStatusResponse | null>(null);
  const [resultFilename, setResultFilename] = useState<string | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    setStatus(null);
    setError(null);
    setResultFilename(null);
    setPreviewUrl(selected ? URL.createObjectURL(selected) : null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setStatus(null);
    setResultFilename(null);

    try {
      const enqueued = await reframeVideo(file, ratio, useYolo);
      setStatus({ job_id: enqueued.job_id, status: enqueued.status });

      const final = await pollVideoStatus(enqueued.job_id, (tick) => setStatus(tick));
      setStatus(final);

      if (final.status === "finished") {
        // output_filename came back from the enqueue response; the
        // job result also carries the full output_path server-side,
        // but the filename is what /video/result/{filename} expects.
        setResultFilename(enqueued.output_filename);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const done = status?.status === "finished" || status?.status === "failed";

  return (
    <div className="uploader">
      <form onSubmit={handleSubmit} className="uploader-form">
        <label className="field">
          <span>Video file</span>
          <input type="file" accept="video/*" onChange={handleFileChange} />
        </label>

        <label className="field">
          <span>Target ratio</span>
          <select value={ratio} onChange={(e) => setRatio(e.target.value)}>
            {RATIOS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>

        <label className="field checkbox">
          <input
            type="checkbox"
            checked={useYolo}
            onChange={(e) => setUseYolo(e.target.checked)}
          />
          <span>Track subject with YOLO</span>
        </label>

        <button type="submit" disabled={!file || loading}>
          {loading ? "Processing…" : "Reframe video"}
        </button>
      </form>

      <p className="hint">
        Video reframing runs as a background job (needs Redis + a worker
        running — <code>python -m app.workers.queue</code>) since a full
        frame-by-frame pass takes longer than a single request.
      </p>

      {error && <p className="error">{error}</p>}

      {status && (
        <div className="batch-panel">
          <p className="batch-status-line">
            Job <code>{status.job_id.slice(0, 8)}</code> — status:{" "}
            <strong>{status.status}</strong>
          </p>

          {!done && <div className="spinner" aria-label="Processing" />}

          {status.status === "failed" && <p className="error">{status.error}</p>}

          {status.status === "finished" && status.result && (
            <p className="hint">
              {status.result.frame_count} frames · {status.result.width}×
              {status.result.height} · {status.result.fps.toFixed(1)} fps
            </p>
          )}
        </div>
      )}

      <div className="preview-grid">
        {previewUrl && (
          <figure>
            <figcaption>Original</figcaption>
            <video src={previewUrl} controls />
          </figure>
        )}

        {resultFilename && status?.status === "finished" && (
          <figure>
            <figcaption>Reframed ({ratio})</figcaption>
            <video src={videoResultUrl(resultFilename)} controls />
          </figure>
        )}
      </div>
    </div>
  );
}
