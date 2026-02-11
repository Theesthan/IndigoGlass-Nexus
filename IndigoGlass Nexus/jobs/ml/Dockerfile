# =============================================================================
# IndigoGlass Nexus - ML Training Job Dockerfile
# =============================================================================

FROM python:3.12-slim

LABEL maintainer="IndigoGlass Team"
LABEL description="ML training job for demand forecasting"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN groupadd --gid 1000 mluser && \
    useradd --uid 1000 --gid mluser --shell /bin/bash --create-home mluser && \
    chown -R mluser:mluser /app

USER mluser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Default command
CMD ["python", "train.py"]
