# Multi-stage build for React frontend with enhanced security
# Build stage
FROM node:18-alpine as builder

# Set build arguments
ARG NODE_ENV=production
ARG REACT_APP_API_URL=/api

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++ \
    && rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies with npm ci for faster, reliable builds
RUN npm ci --silent --no-audit --no-fund \
    && npm cache clean --force

# Copy source code
COPY . .

# Build the application
RUN npm run build \
    && npm run test -- --coverage --watchAll=false --passWithNoTests

# Production stage with nginx
FROM nginx:1.25-alpine as production

# Set labels for better maintainability
LABEL maintainer="DevOps Team" \
      version="1.0.0" \
      description="Namespace Startup Scheduler Frontend" \
      org.opencontainers.image.title="Namespace Startup Scheduler Frontend" \
      org.opencontainers.image.description="React frontend for namespace startup scheduler system" \
      org.opencontainers.image.vendor="Your Organization" \
      org.opencontainers.image.licenses="MIT"

# Install additional security tools
RUN apk add --no-cache \
    curl \
    tini \
    && rm -rf /var/cache/apk/*

# Create non-root user with specific UID/GID
RUN addgroup -g 1001 -S appuser \
    && adduser -S appuser -G appuser -u 1001

# Copy built application from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create nginx directories and set permissions
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /var/log/nginx \
             /var/run \
    && touch /var/run/nginx.pid \
    && chown -R appuser:appuser \
        /var/cache/nginx \
        /var/log/nginx \
        /var/run/nginx.pid \
        /usr/share/nginx/html \
        /etc/nginx/conf.d

# Create health check script
RUN echo '#!/bin/sh' > /usr/local/bin/health-check.sh \
    && echo 'curl -f http://localhost:8080/health >/dev/null 2>&1 || exit 1' >> /usr/local/bin/health-check.sh \
    && chmod +x /usr/local/bin/health-check.sh \
    && chown appuser:appuser /usr/local/bin/health-check.sh

# Switch to non-root user
USER appuser

# Set environment variables
ENV NGINX_WORKER_PROCESSES=auto \
    NGINX_WORKER_CONNECTIONS=1024 \
    NGINX_KEEPALIVE_TIMEOUT=65

# Expose port
EXPOSE 8080

# Health check with improved configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Use tini as init system for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Start nginx
CMD ["nginx", "-g", "daemon off;"]