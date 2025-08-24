# Production-ready multi-stage Dockerfile for n8n Agent API
# Stage 1: Builder - Install dependencies and prepare application
FROM python:3.12-slim as builder

# Set build-time variables
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG VCS_REF

# Add metadata labels
LABEL maintainer="development@example.com" \
      version="${VERSION}" \
      description="n8n Agent API - Intelligent workflow automation" \
      build-date="${BUILD_DATE}" \
      vcs-ref="${VCS_REF}"

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --no-compile -r requirements.txt

# Stage 2: Production - Create minimal runtime image
FROM python:3.12-slim as production

# Set runtime variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8001 \
    HOST=0.0.0.0 \
    LOG_LEVEL=info

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser $VIRTUAL_ENV $VIRTUAL_ENV

# Create app directory and set ownership
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application files with proper ownership
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Configure uvicorn for production
ENV UVICORN_HOST=${HOST} \
    UVICORN_PORT=${PORT} \
    UVICORN_LOG_LEVEL=${LOG_LEVEL} \
    UVICORN_ACCESS_LOG=true \
    UVICORN_WORKERS=1

# Production startup command
CMD ["sh", "-c", "uvicorn main:app --host ${UVICORN_HOST} --port ${UVICORN_PORT} --log-level ${UVICORN_LOG_LEVEL} --access-log --no-use-colors --loop uvloop --http httptools"]