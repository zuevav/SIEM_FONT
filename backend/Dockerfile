# =====================================================================
# SIEM Backend - Dockerfile
# =====================================================================
# Multi-stage build for optimized image size
# Python 3.11+ with FastAPI and PostgreSQL support
# =====================================================================

FROM python:3.11-slim as builder

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =====================================================================
# Final stage - Runtime image
# =====================================================================

FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 siem && \
    chown -R siem:siem /app

# Copy application code
COPY --chown=siem:siem app/ /app/app/
COPY --chown=siem:siem scripts/ /app/scripts/

# Create directories for logs and uploads
RUN mkdir -p /app/logs /app/uploads && \
    chown -R siem:siem /app/logs /app/uploads

# Switch to non-root user
USER siem

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
