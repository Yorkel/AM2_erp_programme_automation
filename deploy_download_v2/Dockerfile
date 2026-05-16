# 1. Start from minimal Python image
FROM python:3.11-slim

# 2. Set working directory inside the container
WORKDIR /app

# 3. Copy requirements first (for Docker layer caching)
COPY requirements-api.txt .

# 4. Install Python dependencies
RUN pip install --no-cache-dir -r requirements-api.txt

# 5. Download spaCy language model (needed for preprocessing)
RUN python -m spacy download en_core_web_sm

# 6. Copy the application code
COPY model_pipeline/ model_pipeline/

# 7. Copy trained model artefacts
COPY experiments/outputs/runs/ experiments/outputs/runs/

# 8. Copy config file
COPY config.yaml .

# 9. Document the port the API listens on
EXPOSE 8000

# 10. Start the API server
CMD ["uvicorn", "model_pipeline.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
