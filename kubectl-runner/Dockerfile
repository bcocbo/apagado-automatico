# kubectl runner container for EKS tasks
FROM alpine:3.18

# Install necessary packages
RUN apk add --no-cache \
    curl \
    wget \
    bash \
    python3 \
    py3-pip \
    jq \
    git \
    openssh-client \
    ca-certificates \
    openssl \
    && rm -rf /var/cache/apk/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl \
    && mv kubectl /usr/local/bin/

# Install AWS CLI v2
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip

# Install helm
RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install additional tools
RUN pip3 install --no-cache-dir \
    flask==2.3.3 \
    flask-cors==4.0.0 \
    kubernetes \
    boto3==1.28.85 \
    croniter==1.4.1 \
    pyyaml==6.0.1 \
    requests==2.31.0 \
    python-dateutil==2.8.2

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Create directories for logs and configs
RUN mkdir -p /app/logs /app/config /root/.kube

# Expose port for API
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application
CMD ["python3", "app.py"]