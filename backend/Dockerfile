FROM python:3.13-slim

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
        xz-utils \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz \
    -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 \
    && rm /tmp/node.tar.xz \
    && node --version \
    && npm --version

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install the PO-token provider server
RUN git clone --single-branch --branch 2.0.0 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && npm ci \
    && npx tsc

# Copy application
COPY app.py .

COPY templates ./templates
COPY static ./static

RUN mkdir -p downloads

ENV FLASK_DEBUG=false

EXPOSE 5000

CMD ["sh", "-c", "node /opt/bgutil-ytdlp-pot-provider/server/build/main.js & gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 900 app:app"]