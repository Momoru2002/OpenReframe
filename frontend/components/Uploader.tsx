"use client";

import { useState } from "react";
import {
  reframeImage,
  reframeImagesBatch,
  pollBatchStatus,
  resultUrl,
  ReframeResponse,
  BatchStatusResponse,
} from "@/lib/api";

const RATIOS = ["9:16", "1:1", "4:5", "16:9", "4:3"];

export default function Uploader() {
  const [files, setFiles] = useState<File[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [ratio, setRatio] = useState("9:16");
  const [useYolo, setUseYolo] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Single-image result (used when exactly 1 file is selected).
  const [result, setResult] = useState<ReframeResponse | null>(null);

  // Batch result (used when 2+ files are selected).
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = Array.from(e.target.files ?? []);
    setFiles(selected);
    setResult(null);
    setBatchStatus(null);
    setError(null);

    if (selected.length === 1) {
      setPreviewUrl(URL.createObjectURL(selected[0]));
    } else {
      setPreviewUrl(null);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setBatchStatus(null);

    try {
      if (files.length === 1) {
        const response = await reframeImage(files[0], ratio, useYolo);
        setResult(response);
      } else {
        const enqueued = await reframeImagesBatch(files, ratio, useYolo);
        setBatchStatus({ job_id: enqueued.job_id, status: enqueued.status });
        const final = await pollBatchStatus(enqueued.job_id, (tick) => setBatchStatus(tick));
        setBatchStatus(final);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const isBatch = files.length > 1;
  const batchDone = batchStatus?.status === "finished" || batchStatus?.status === "failed";

  return (
    <div className="uploader">
      <form onSubmit={handleSubmit} className="uploader-form">
        <label className="field">
          <span>Media files</span>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileChange}
          />
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
          <span>Use YOLO subject detection</span>
        </label>

        <button type="submit" disabled={files.length === 0 || loading}>
          {loading
            ? isBatch
              ? "Processing batch…"
              : "Reframing…"
            : isBatch
            ? `Reframe ${files.length} photos`
            : "Reframe"}
        </button>
      </form>

      {files.length > 1 && (
        <p className="hint">{files.length} files selected — will run as a batch job.</p>
      )}

      {error && <p className="error">{error}</p>}

      {/* Single-image preview */}
      {!isBatch && (
        <div className="preview-grid">
          {previewUrl && (
            <figure>
              <figcaption>Original</figcaption>
              <img src={previewUrl} alt="Original upload" />
            </figure>
          )}

          {result && (
            <figure>
              <figcaption>
                Reframed ({result.ratio}) —{" "}
                {result.subject_detected
                  ? `subject: ${result.subject?.label}`
                  : "no subject detected"}
              </figcaption>
              <img src={resultUrl(result.filename)} alt="Reframed result" />
            </figure>
          )}
        </div>
      )}

      {/* Batch progress + results */}
      {isBatch && batchStatus && (
        <div className="batch-panel">
          <p className="batch-status-line">
            Job <code>{batchStatus.job_id.slice(0, 8)}</code> — status:{" "}
            <strong>{batchStatus.status}</strong>
            {batchDone && batchStatus.status === "finished" && (
              <>
                {" "}
                — {batchStatus.succeeded} succeeded, {batchStatus.failed} failed
              </>
            )}
          </p>

          {!batchDone && <div className="spinner" aria-label="Processing" />}

          {batchStatus.status === "failed" && (
            <p className="error">{batchStatus.error}</p>
          )}

          {batchStatus.status === "finished" && batchStatus.results && (
            <div className="batch-grid">
              {batchStatus.results.map((r) => (
                <figure key={r.source_filename} className={r.success ? "" : "batch-item-failed"}>
                  {r.success && r.filename ? (
                    <img src={resultUrl(r.filename)} alt={r.source_filename} />
                  ) : (
                    <div className="batch-item-error-box">⚠️</div>
                  )}
                  <figcaption>
                    {r.source_filename}
                    {!r.success && ` — ${r.error}`}
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
