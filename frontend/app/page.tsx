"use client";

import { useState } from "react";
import Uploader from "@/components/Uploader";
import VideoUploader from "@/components/VideoUploader";

export default function Page() {
  const [tab, setTab] = useState<"image" | "video">("image");

  return (
    <main className="page">
      <h1>🎬 OpenReframe</h1>
      <p className="tagline">
        Subject-aware reframing for images and video — pick a target ratio
        and let YOLO find the subject to crop (or track) around.
      </p>

      <div className="tabs">
        <button
          className={tab === "image" ? "tab tab-active" : "tab"}
          onClick={() => setTab("image")}
        >
          🖼️ Images
        </button>
        <button
          className={tab === "video" ? "tab tab-active" : "tab"}
          onClick={() => setTab("video")}
        >
          🎞️ Video
        </button>
      </div>

      {tab === "image" ? <Uploader /> : <VideoUploader />}
    </main>
  );
}
