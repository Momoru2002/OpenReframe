export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SubjectBox {
  label: string;
  confidence: number;
  box?: [number, number, number, number];
}

export interface ReframeResponse {
  success: boolean;
  filename: string;
  saved_to: string;
  width: number;
  height: number;
  ratio: string;
  subject_detected: boolean;
  subject: SubjectBox | null;
}

export async function reframeImage(
  file: File,
  ratio: string,
  useYolo: boolean
): Promise<ReframeResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("ratio", ratio);
  form.append("use_yolo", String(useYolo));

  const res = await fetch(`${API_BASE}/image/reframe`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export function resultUrl(filename: string): string {
  return `${API_BASE}/image/result/${encodeURIComponent(filename)}`;
}

export function videoResultUrl(filename: string): string {
  return `${API_BASE}/video/result/${encodeURIComponent(filename)}`;
}

export async function listRatios(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/image/ratios`);
  if (!res.ok) return ["9:16", "1:1", "4:5", "16:9"];
  const data = await res.json();
  return data.presets;
}

// ---------------------------------------------------------------------
// Batch image reframing (many photos at once, processed as a background
// job — same job_id + poll pattern as video below).
// ---------------------------------------------------------------------

export interface BatchEnqueueResponse {
  job_id: string;
  status: string;
  file_count: number;
}

export interface BatchResultItem {
  success: boolean;
  source_filename: string;
  filename?: string;
  width?: number;
  height?: number;
  subject_detected?: boolean;
  subject?: SubjectBox | null;
  error?: string;
}

export interface BatchStatusResponse {
  job_id: string;
  status: "queued" | "started" | "deferred" | "finished" | "failed" | string;
  results?: BatchResultItem[];
  succeeded?: number;
  failed?: number;
  error?: string;
}

export async function reframeImagesBatch(
  files: File[],
  ratio: string,
  useYolo: boolean
): Promise<BatchEnqueueResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  form.append("ratio", ratio);
  form.append("use_yolo", String(useYolo));

  const res = await fetch(`${API_BASE}/image/reframe-batch`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export async function getBatchStatus(jobId: string): Promise<BatchStatusResponse> {
  const res = await fetch(`${API_BASE}/image/batch-status/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

/** Poll a batch job until it's finished or failed. Calls onTick after
 * every poll so the UI can show live status while waiting. */
export async function pollBatchStatus(
  jobId: string,
  onTick?: (status: BatchStatusResponse) => void,
  intervalMs = 2000
): Promise<BatchStatusResponse> {
  while (true) {
    const status = await getBatchStatus(jobId);
    onTick?.(status);
    if (status.status === "finished" || status.status === "failed") {
      return status;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

// ---------------------------------------------------------------------
// Video reframing (async job + poll, mirrors the batch image flow).
// ---------------------------------------------------------------------

export interface VideoEnqueueResponse {
  job_id: string;
  status: string;
  output_filename: string;
}

export interface VideoJobResult {
  output_path: string;
  frame_count: number;
  fps: number;
  width: number;
  height: number;
}

export interface VideoStatusResponse {
  job_id: string;
  status: "queued" | "started" | "deferred" | "finished" | "failed" | string;
  result?: VideoJobResult;
  error?: string;
}

export async function reframeVideo(
  file: File,
  ratio: string,
  useYolo: boolean
): Promise<VideoEnqueueResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("ratio", ratio);
  form.append("use_yolo", String(useYolo));

  const res = await fetch(`${API_BASE}/video/reframe`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

export async function getVideoStatus(jobId: string): Promise<VideoStatusResponse> {
  const res = await fetch(`${API_BASE}/video/status/${encodeURIComponent(jobId)}`);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function pollVideoStatus(
  jobId: string,
  onTick?: (status: VideoStatusResponse) => void,
  intervalMs = 3000
): Promise<VideoStatusResponse> {
  while (true) {
    const status = await getVideoStatus(jobId);
    onTick?.(status);
    if (status.status === "finished" || status.status === "failed") {
      return status;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
