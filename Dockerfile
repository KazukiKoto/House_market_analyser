FROM python:3.12-slim
# Set working directory
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY dashboard.py .
COPY scraper.py .
COPY init_db.py .
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