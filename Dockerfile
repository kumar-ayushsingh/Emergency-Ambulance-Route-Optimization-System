# ==============================================================================
# Stage 1: Build the React + Leaflet Single-Page Application (Frontend)
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install package dependencies using package lockfile
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source code and compile production distribution
COPY frontend/ ./
RUN npm run build

# ==============================================================================
# Stage 2: Production Runtime with Python 3.11-slim
# ==============================================================================
FROM python:3.11-slim

# Prevent python from buffering stdout/stderr and writing bytecode
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install minimal OS utilities for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend Python code and offline spatial datasets
# data/srinagar.graphml and data/bengaluru.graphml ensure startup never downloads from OpenStreetMap
COPY backend/ ./backend/
COPY data/ ./data/

# Copy compiled frontend static assets from Stage 1 into frontend/dist
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose default listening port
EXPOSE 8000

# Run uvicorn on dynamic port $PORT with a single worker, no reload, no debug
CMD ["sh", "-c", "exec uvicorn backend.api:app --host 0.0.0.0 --port $PORT --workers 1"]
