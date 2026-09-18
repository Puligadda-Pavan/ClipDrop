from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file
from yt_dlp import YoutubeDL


# =========================================================
# Flask application
# =========================================================

app = Flask(__name__)


# =========================================================
# Download directory
# =========================================================

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


# =========================================================
# CORS configuration
# =========================================================

allowed_origins = {
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
}


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    if "*" in allowed_origins or origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = (
            "*"
            if "*" in allowed_origins
            else origin
        )

        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    return response


# =========================================================
# In-memory download jobs
# =========================================================

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()


# =========================================================
# Update job helper
# =========================================================

def update_job(job_id: str, **changes: Any) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(changes)


# =========================================================
# Download worker
# =========================================================

def run_download(job_id: str, url: str) -> None:

    output_template = str(
        DOWNLOAD_DIR / f"{job_id}.%(ext)s"
    )


    # -----------------------------------------------------
    # Progress hook
    # -----------------------------------------------------

    def progress_hook(data: dict[str, Any]) -> None:

        status = data.get("status")

        if status == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
                or 0
            )

            percent = (
                round(downloaded / total * 100)
                if total
                else 0
            )

            update_job(
                job_id,

                status="downloading",

                progress=min(
                    percent,
                    99
                ),

                speed=data.get(
                    "_speed_str",
                    ""
                ),

                eta=data.get(
                    "_eta_str",
                    ""
                ),
            )


        elif status == "finished":

            update_job(
                job_id,

                status="processing",

                progress=99
            )


    # -----------------------------------------------------
    # yt-dlp options
    # -----------------------------------------------------

    options = {

        # Best available video + audio
        "format": "bestvideo+bestaudio/best",

        # Merge separate streams into MP4
        "merge_output_format": "mp4",

        # Output filename
        "outtmpl": output_template,

        # Don't download playlists
        "noplaylist": True,

        # Progress reporting
        "progress_hooks": [
            progress_hook
        ],

        # Logging
        "quiet": False,
        "no_warnings": False,
        "verbose": True,


        # -------------------------------------------------
        # JavaScript runtime
        # -------------------------------------------------

        "js_runtimes": {
            "node": {}
        },


        # -------------------------------------------------
        # bgutil PO Token Provider
        # -------------------------------------------------

        "extractor_args": {
            "youtubepot-bgutilhttp": {
                "base_url": "http://127.0.0.1:4416"
            }
        },
    }


    # -----------------------------------------------------
    # Run download
    # -----------------------------------------------------

    try:

        update_job(
            job_id,

            status="starting",

            progress=0
        )


        with YoutubeDL(options) as ydl:

            ydl.download([url])


        # -------------------------------------------------
        # Find downloaded file
        # -------------------------------------------------

        files = [
            path
            for path in DOWNLOAD_DIR.glob(
                f"{job_id}.*"
            )
            if path.is_file()
        ]


        if not files:

            raise RuntimeError(
                "The download finished but no output file was found."
            )


        output_file = max(
            files,
            key=lambda path: path.stat().st_mtime
        )


        # -------------------------------------------------
        # Mark complete
        # -------------------------------------------------

        update_job(

            job_id,

            status="complete",

            progress=100,

            filename=output_file.name,

            path=str(output_file)
        )


    except Exception as error:

        update_job(

            job_id,

            status="error",

            error=str(error),

            progress=0
        )


# =========================================================
# Home page
# =========================================================

@app.get("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# Create download
# =========================================================

@app.post("/api/download")
def create_download():

    payload = (
        request.get_json(
            silent=True
        )
        or {}
    )


    url = str(
        payload.get(
            "url",
            ""
        )
    ).strip()


    # -----------------------------------------------------
    # Basic URL validation
    # -----------------------------------------------------

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):

        return jsonify(
            {
                "error":
                    "Enter a valid video URL starting with http:// or https://."
            }
        ), 400


    # -----------------------------------------------------
    # Create job
    # -----------------------------------------------------

    job_id = uuid.uuid4().hex


    with jobs_lock:

        jobs[job_id] = {

            "status": "queued",

            "progress": 0,

            "speed": "",

            "eta": ""
        }


    # -----------------------------------------------------
    # Start background download
    # -----------------------------------------------------

    thread = threading.Thread(

        target=run_download,

        args=(
            job_id,
            url
        ),

        daemon=True
    )

    thread.start()


    return jsonify(
        {
            "job_id": job_id
        }
    ), 202


# =========================================================
# Download status
# =========================================================

@app.get("/api/download/<job_id>")
def download_status(
    job_id: str
):

    with jobs_lock:

        job = jobs.get(
            job_id
        )


        if not job:

            return jsonify(
                {
                    "error":
                        "Download job not found."
                }
            ), 404


        response = dict(job)


    # -----------------------------------------------------
    # Add download URL when complete
    # -----------------------------------------------------

    if response.get(
        "status"
    ) == "complete":

        response["download_url"] = (
            f"/api/download/{job_id}/file"
        )


    return jsonify(
        response
    )


# =========================================================
# Download completed file
# =========================================================

@app.get("/api/download/<job_id>/file")
def get_download(
    job_id: str
):

    with jobs_lock:

        job = jobs.get(
            job_id
        )


    if (
        not job
        or job.get("status")
        != "complete"
    ):

        return jsonify(
            {
                "error":
                    "This download is not ready."
            }
        ), 404


    return send_file(

        job["path"],

        as_attachment=True,

        download_name=job["filename"]
    )


# =========================================================
# Local development
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.getenv(
                "PORT",
                "5000"
            )
        ),

        debug=(
            os.getenv(
                "FLASK_DEBUG",
                "false"
            ).lower()
            == "true"
        )
    )