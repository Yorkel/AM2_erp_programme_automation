# Dockerfile — AM2 ERP newsletter classifier serving image.
#
# Build:    docker build -t am2-classifier .
# Run:      docker run -p 8000:8000 am2-classifier
# Deploy:   Hugging Face Spaces builds this Docker image from the repo root.

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
# 4a. Install CPU-only torch FIRST from the PyTorch CPU wheel index. The default
#     PyPI torch wheel bundles multi-GB CUDA/nvidia libraries we never use — this
#     host has no GPU. Its own cached layer means it isn't re-fetched when the
#     other requirements change.
RUN pip install --no-cache-dir torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu
# 4b. Install the rest. pip sees torch==2.11.0 already satisfied and keeps the CPU
#     build instead of pulling the CUDA one.
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

# 7. Port the API listens on. Hosts may pass $PORT at runtime; the CMD below
#    reads it and falls back to 8000 locally / on Hugging Face Spaces.
EXPOSE 8000

# 8. Start the server. Use the shell form so $PORT env-var expansion works.
CMD uvicorn src.serving.api:app --host 0.0.0.0 --port ${PORT:-8000}
