# Multi-stage Dockerfile to build and run both backend and frontend

# Stage 1: Build backend
FROM python:3.11-slim AS backend-builder

WORKDIR /app

# Copy backend requirements first for better caching
# Note: No system dependencies needed - Python packages use pre-built wheels
COPY backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Copy backend application code
COPY backend/ /app/

# Stage 2: Build frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files for dependency installation
COPY frontend/package.json frontend/package-lock.json ./

# Install all dependencies (including devDependencies for build)
RUN npm ci

# Copy application source code
COPY frontend/ .

# Build the production application
RUN npm run build

# Prune dev dependencies for production
RUN npm prune --production

# Stage 3: Final stage - combine both services (PRODUCTION)
FROM python:3.11-slim

WORKDIR /app

# Install nginx and Node.js for reverse proxy and frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy backend from builder stage
COPY --from=backend-builder /app /app/backend

# Copy frontend build from builder stage (production build only)
COPY --from=frontend-builder /app/build /app/frontend/build
COPY --from=frontend-builder /app/node_modules /app/frontend/node_modules
COPY --from=frontend-builder /app/package.json /app/frontend/package.json

# Copy CSV data directory (needed for simulation)
COPY Valmet-HSY-Docs/ /Valmet-HSY-Docs/

# Production environment variables
ENV PYTHONPATH=/app/backend
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cloud Run sets PORT environment variable, default to 8080 for Cloud Run
ENV PORT=8080
ENV BACKEND_PORT=8000
ENV FRONTEND_PORT=5173

# Copy configuration files
COPY nginx.conf /etc/nginx/sites-available/app
COPY start.sh /app/start.sh

# Create production wrapper scripts for backend and frontend
RUN echo '#!/bin/bash' > /app/start-backend.sh && \
    echo 'set -e' >> /app/start-backend.sh && \
    echo 'cd /app/backend' >> /app/start-backend.sh && \
    echo 'export PYTHONUNBUFFERED=1' >> /app/start-backend.sh && \
    echo 'export PYTHONDONTWRITEBYTECODE=1' >> /app/start-backend.sh && \
    echo '# Production: use uvicorn with workers for better performance' >> /app/start-backend.sh && \
    echo 'uvicorn api.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-8000} --workers 2 --log-level info --access-log' >> /app/start-backend.sh && \
    chmod +x /app/start-backend.sh

RUN echo '#!/bin/bash' > /app/start-frontend.sh && \
    echo 'set -e' >> /app/start-frontend.sh && \
    echo 'cd /app/frontend' >> /app/start-frontend.sh && \
    echo 'export NODE_ENV=production' >> /app/start-frontend.sh && \
    echo 'export PORT=${FRONTEND_PORT:-5173}' >> /app/start-frontend.sh && \
    echo 'export HOST=0.0.0.0' >> /app/start-frontend.sh && \
    echo '# Production: start Node.js server' >> /app/start-frontend.sh && \
    echo 'if [ -f build/server.js ]; then' >> /app/start-frontend.sh && \
    echo '  exec node build/server.js' >> /app/start-frontend.sh && \
    echo 'elif [ -f build/index.js ]; then' >> /app/start-frontend.sh && \
    echo '  exec node build/index.js' >> /app/start-frontend.sh && \
    echo 'else' >> /app/start-frontend.sh && \
    echo '  exec node build' >> /app/start-frontend.sh && \
    echo 'fi' >> /app/start-frontend.sh && \
    chmod +x /app/start-frontend.sh

# Configure nginx for production
# Disable nginx version disclosure for security
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app && \
    sed -i 's/# server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf || true && \
    echo 'server_tokens off;' >> /etc/nginx/nginx.conf

# Health check endpoint (for Cloud Run)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Expose ports (Cloud Run will use PORT env var, but we expose both for clarity)
EXPOSE 8080 8000 5173

# Production: Start script which configures nginx and starts both services
CMD ["/app/start.sh"]
