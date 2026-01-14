# Multi-stage Dockerfile for Moxy
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend (production build)
# In Docker, frontend is served from same origin as backend, so use empty string for relative URLs
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Stage 2: Backend and runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN pip install --no-cache-dir uv

# Copy backend files
COPY backend/ ./

# Install Python dependencies using uv
# uv will read pyproject.toml and install all dependencies
RUN uv pip install --system .

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create projects_data directory for persistence
RUN mkdir -p projects_data

# Expose ports
# 5000: Backend API
# 8080: Frontend (served by backend in production)
# 8081: Proxy
EXPOSE 5000 8080 8081

# Set environment variables
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "main.py"]
