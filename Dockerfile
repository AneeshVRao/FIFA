# Stage 1: Build React Assets
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Serve via FastAPI Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies if needed (e.g. build-essential for packages compiling C)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python application files
COPY backend/ ./backend
COPY data/ ./data
COPY run.py .

# Copy built frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set env variables
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
