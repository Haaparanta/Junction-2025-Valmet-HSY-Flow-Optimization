FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ /app/

# Copy CSV data directory (needed for simulation)
# The code expects Valmet-HSY-Docs at the root level (parent.parent from /app)
COPY Valmet-HSY-Docs/ /Valmet-HSY-Docs/

# Set Python path
ENV PYTHONPATH=/app

# Run main.py
CMD ["python", "main.py"]

