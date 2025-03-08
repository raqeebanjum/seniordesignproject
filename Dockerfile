# Build frontend
FROM node:18 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
RUN npm run build

# Build the backend
FROM python:3.11-slim
WORKDIR /app

# Installing system dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire backend directory structure
COPY backend/ ./backend/

# Create audio directories
RUN mkdir -p backend/data/audio backend/data/ai_audio

# Copy built frontend files
COPY --from=frontend-builder /app/frontend/dist ./backend/static/

EXPOSE 5001

# Change working directory to backend
WORKDIR /app/backend

CMD ["python", "app.py"]