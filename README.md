# Clipdrop

A web frontend and Python download backend for downloading a single online video as an MP4 with `yt-dlp`.

## Project layout

- `frontend/`: deploy to Netlify, Vercel, or Cloudflare Pages.
- `backend/`: deploy to Render, Railway, Fly.io, or a Docker-capable VPS.
- `backend/downloads/`: temporary backend output files.

## Run

```powershell
cd backend
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in a browser.

`ffmpeg` must be installed and available on your PATH so separate video and audio streams can be merged into an MP4.

## Deploying

Deploy the `frontend/` folder to Netlify, Vercel, or Cloudflare Pages. Deploy the `backend/` folder to a service that supports long-running Python processes and `ffmpeg`, such as Render, Railway, Fly.io, or a VPS.

Set `frontend/static/config.js` before deploying the frontend:

```javascript
window.DOWNLOADER_API_URL = "https://your-backend.example.com";
```

On the backend, set `ALLOWED_ORIGINS` to the frontend URL, for example `https://your-site.netlify.app`. The backend also accepts `PORT` and `FLASK_DEBUG` environment variables.

For a container-based backend, use `backend/Dockerfile` with `backend/` as the Docker build context. It installs `ffmpeg` and starts the app with Gunicorn.
