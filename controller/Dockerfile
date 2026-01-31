# Multi-stage build for optimized size and security
# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG KUBECTL_VERSION=v1.29.0
ARG TARGETPLATFORM
ARG BUILDPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set architecture for kubectl download
RUN case ${TARGETPLATFORM} in \
        "linux/amd64") ARCH=amd64 ;; \
        "linux/arm64") ARCH=arm64 ;; \
        *) ARCH=amd64 ;; \
    esac \
    && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl" \
    && curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}/kubectl.sha256" \
    && echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/kubectl

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip list --format=freeze > /tmp/installed-packages.txt

# Production stage
FROM python:3.11-slim as production

# Set labels for better maintainability
LABEL maintainer="DevOps Team" \
      version="1.0.0" \
      description="Namespace Auto-Shutdown Controller" \
      org.opencontainers.image.title="Namespace Controller" \
      org.opencontainers.image.description="Kubernetes namespace auto-shutdown controller" \
      org.opencontainers.image.vendor="Your Organization" \
      org.opencontainers.image.licenses="MIT"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create non-root user with specific UID/GID
RUN groupadd -g 1001 -r appuser \
    && useradd -r -g appuser -u 1001 -m -d /home/appuser -s /bin/bash appuser

# Copy kubectl from builder
COPY --from=builder /usr/local/bin/kubectl /usr/local/bin/kubectl

# Copy Python virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=appuser:appuser . .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/tmp \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Expose port for metrics and health checks
EXPOSE 8080

# Health check with improved reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]