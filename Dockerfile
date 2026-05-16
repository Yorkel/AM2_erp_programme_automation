# Dockerfile — AM2 ERP newsletter classifier serving image.
#
# Build:    docker build -t am2-classifier .
# Run:      docker run -p 8000:8000 am2-classifier
# Deploy:   Render auto-builds this on every push to main (see render.yaml).

# 1. Base image — Python 3.12 slim (small, single-purpose).
FROM python:3.12-slim

# 2. Avoid Python writing .pyc files and buffering stdout in the container.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 3. Working directory inside the container.
WORKDIR /app

# 4. Install dependencies first (separate layer so Docker can cache).
#    The api-only requirements file is much smaller than requirements.txt.
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# 5. Pre-download the sentence-transformer model into the image so the first
#    /predict isn't slow. Without this line, the model downloads on first
#    request (~80 MB, takes 5-15 seconds and depends on network).
RUN python -c "from sentence_transformers import SentenceTransformer; \
               SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# 6. Copy only what the serving code needs.
COPY src/serving/ src/serving/
COPY src/__init__.py src/__init__.py
COPY models/runs/ models/runs/

# 7. Port the API listens on. Render passes its own $PORT env var at runtime,
#    so the CMD below reads it (falls back to 8000 locally).
EXPOSE 8000

# 8. Start the server. Use the shell form so $PORT env-var expansion works.
CMD uvicorn src.serving.api:app --host 0.0.0.0 --port ${PORT:-8000}
