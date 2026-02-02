# Build Stage for Frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app/web

# Copy package files
COPY web/package*.json ./
RUN npm install

# Copy source code
COPY web/ .

# Build frontend
RUN npm run build


# Runtime Stage
FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TGF_DATA_DIR=/data \
    TGF_WEB_DIST=/app/static

# Install system dependencies
# gcc/python3-dev might be needed for some python packages (e.g. aiosqlite build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY api/ ./api/
COPY tgf/ ./tgf/

# Copy frontend build from builder stage
COPY --from=frontend-builder /app/web/dist /app/static

# Create data directory volume
VOLUME /data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
