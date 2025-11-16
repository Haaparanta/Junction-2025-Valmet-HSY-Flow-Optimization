FROM python:3.11-slim

WORKDIR /app

# Optional: install system deps if you actually need them
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#  && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first for caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python deps (PyTorch CPU extra index)
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Copy backend code
COPY backend/ /app/

# Copy CSV data to expected root-level path
COPY Valmet-HSY-Docs/ /Valmet-HSY-Docs/

# Python path and Cloud Run port
ENV PYTHONPATH=/app
ENV PORT=8000

# Cloud Run: PORT is injected → use shell form so env is expanded
CMD sh -c "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"
