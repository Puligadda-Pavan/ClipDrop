from __future__ import annotations

import threading
import uuid
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)
allowed_origins = {
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
}

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if "*" in allowed_origins or origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = "*" if "*" in allowed_origins else origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def update_job(job_id: str, **changes: Any) -> None:
    with jobs_lock:
        jobs[job_id].update(changes)


def run_download(job_id: str, url: str) -> None:
    output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")

    def progress_hook(data: dict[str, Any]) -> None:
        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes", 0)
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            percent = round(downloaded / total * 100) if total else 0
            update_job(
                job_id,
                status="downloading",
                progress=min(percent, 99),
                speed=data.get("_speed_str", ""),
                eta=data.get("_eta_str", ""),
            )
        elif status == "finished":
            update_job(job_id, status="processing", progress=99)

    options = {
    "format": "best/bestvideo+bestaudio",
    "merge_output_format": "mp4",
    "outtmpl": output_template,
    "noplaylist": True,
    "progress_hooks": [progress_hook],

    "quiet": False,
    "no_warnings": False,
    "verbose": True,

    "js_runtimes": {
        "node": {}
    },

    "extractor_args": {
        "youtube": {
            "player_client": ["tv"]
        }
    }
}

    try:
        update_job(job_id, status="starting", progress=0)
        with YoutubeDL(options) as ydl:
            ydl.download([url])

        files = [path for path in DOWNLOAD_DIR.glob(f"{job_id}.*") if path.is_file()]
        if not files:
            raise RuntimeError("The download finished but no output file was found.")
        output_file = max(files, key=lambda path: path.stat().st_mtime)
        update_job(
            job_id,
            status="complete",
            progress=100,
            filename=output_file.name,
            path=str(output_file),
        )
    except Exception as error:
        update_job(job_id, status="error", error=str(error), progress=0)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/download")
def create_download():
    payload = request.get_json(silent=True) or {}
    url = str(payload.get("url", "")).strip()

    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Enter a valid video URL starting with http:// or https://."}), 400

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "queued", "progress": 0, "speed": "", "eta": ""}

    thread = threading.Thread(target=run_download, args=(job_id, url), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id}), 202


@app.get("/api/download/<job_id>")
def download_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Download job not found."}), 404
        response = dict(job)

    if response.get("status") == "complete":
        response["download_url"] = f"/api/download/{job_id}/file"
    return jsonify(response)


@app.get("/api/download/<job_id>/file")
def get_download(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job or job.get("status") != "complete":
        return jsonify({"error": "This download is not ready."}), 404
    return send_file(job["path"], as_attachment=True, download_name=job["filename"])


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
