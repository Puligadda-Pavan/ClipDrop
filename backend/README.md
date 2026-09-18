# Clipdrop backend

This Flask service runs `yt-dlp` and `ffmpeg` and exposes the download API.

## Local run

```powershell
python -m pip install -r requirements.txt
python app.py
```

## Deployment

Deploy this folder as a Docker service using `Dockerfile`. Set:

```text
ALLOWED_ORIGINS=https://your-frontend.example.com
```

The service reads `PORT` from the hosting provider and stores temporary output in `downloads/`.
