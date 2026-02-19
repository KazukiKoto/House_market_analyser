# Stage 1: Frontend builder
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python dependencies builder
FROM python:3.12-slim AS python-builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 3: Final runtime
FROM python:3.12-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/static /app/static

# Copy application files
COPY dashboard.py .
COPY scraper.py .
COPY scheduler.py .
COPY init_db.py .
COPY migrate_db.py .
COPY entrypoint.sh .
COPY templates/ templates/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Directory for SQLite database
RUN mkdir -p /app/data

# Create healthcheck script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8000/ || exit 1' > /app/healthcheck.sh && chmod +x /app/healthcheck.sh

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh

EXPOSE 8000

# Environment variable for database path
ENV DB_PATH=/app/data/properties.db

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["uvicorn", "dashboard:app", "--host", "0.0.0.0", "--port", "8000"]

# Build and start: docker-compose up -d