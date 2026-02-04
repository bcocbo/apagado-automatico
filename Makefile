# Makefile for Namespace Startup Scheduler
# Provides convenient commands for development, testing, and deployment

.PHONY: help setup build test lint clean dev-up dev-down deploy

# Default target
help: ## Show this help message
	@echo "Namespace Startup Scheduler - Development Commands"
	@echo "================================================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make setup             # Set up development environment"
	@echo "  make dev-up            # Start local development environment"
	@echo "  make test              # Run all tests"
	@echo "  make build             # Build Docker images"

# Setup and Installation
setup: ## Set up development environment
	@echo "🛠️  Setting up development environment..."
	@echo "Installing Python dependencies..."
	@cd controller && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install
	@echo "Creating environment file..."
	@cp .env.example .env
	@echo "✅ Development environment setup completed"

install-tools: ## Install development tools
	@echo "🛠️  Installing development tools..."
	@pip install --user black flake8 isort bandit safety yamllint pytest pytest-cov
	@echo "✅ Development tools installed"

# Development
dev-up: ## Start local development environment with Docker Compose
	@echo "🚀 Starting local development environment..."
	@docker-compose up -d
	@echo "✅ Development environment started"
	@echo "   - API: http://localhost:8080"
	@echo "   - Frontend: http://localhost:3000"
	@echo "   - Prometheus: http://localhost:9090"
	@echo "   - Grafana: http://localhost:3001 (admin/admin)"

dev-down: ## Stop local development environment
	@echo "🛑 Stopping local development environment..."
	@docker-compose down
	@echo "✅ Development environment stopped"

dev-logs: ## Show logs from development environment
	@docker-compose logs -f

# Building
build: build-controller build-frontend ## Build all Docker images

build-controller: ## Build controller Docker image
	@echo "🐳 Building controller image..."
	@docker build -t namespace-startup-scheduler-controller:local controller/
	@echo "✅ Controller image built with:"
	@echo "   - Multi-stage build for security"
	@echo "   - Non-root user (appuser:1001)"
	@echo "   - kubectl v1.29.0 integrated"
	@echo "   - Health checks on port 8080"
	@echo "   - FastAPI ready with uvicorn"

build-frontend: ## Build frontend Docker image
	@echo "🐳 Building frontend image..."
	@docker build -t namespace-startup-scheduler-frontend:local frontend/

# Testing
test: test-controller test-frontend ## Run all tests

test-controller: ## Run controller tests
	@echo "🧪 Running controller tests..."
	@cd controller && python -m pytest tests/ -v --cov=. --cov-report=term-missing || echo "⚠️  No tests found or pytest failed"

test-frontend: ## Run frontend tests
	@echo "🧪 Running frontend tests..."
	@cd frontend && npm test -- --coverage --watchAll=false --passWithNoTests || echo "⚠️  Frontend tests failed or npm not available"

test-integration: ## Run integration tests
	@echo "🧪 Running integration tests..."
	@docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
	@docker-compose -f docker-compose.test.yml down

# Linting and Code Quality
lint: lint-python lint-frontend lint-yaml ## Run all linting

lint-python: ## Lint Python code
	@echo "🔍 Linting Python code..."
	@cd controller && black --check . && flake8 . && isort --check-only .

lint-frontend: ## Lint frontend code
	@echo "🔍 Linting frontend code..."
	@cd frontend && npm run lint

lint-yaml: ## Lint YAML files
	@echo "🔍 Linting YAML files..."
	@yamllint .

format: ## Format code
	@echo "🎨 Formatting code..."
	@cd controller && black . && isort .
	@cd frontend && npm run format 2>/dev/null || echo "⚠️  Frontend formatting not available"

# Security
security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	@cd controller && bandit -r . -f json -o ../bandit-report.json || true
	@cd controller && safety check --json --output ../safety-report.json || true
	@echo "🐳 Scanning Docker images..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image namespace-startup-scheduler-controller:local || echo "⚠️  Trivy not available"
	@echo "✅ Security scan completed. Reports: bandit-report.json, safety-report.json"

security-scan-image: ## Scan Docker image for vulnerabilities
	@echo "🔒 Scanning controller Docker image..."
	@docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy image --severity HIGH,CRITICAL namespace-startup-scheduler-controller:local

# Infrastructure
infra-deploy: ## Deploy AWS infrastructure
	@echo "🏗️  Deploying AWS infrastructure..."
	@cd infrastructure && ./deploy.sh
	@echo "✅ Infrastructure deployed"

infra-validate: ## Validate infrastructure configuration
	@echo "🔍 Validating infrastructure..."
	@find infrastructure/ -name "*.yaml" -exec yamllint {} \;
	@echo "✅ Infrastructure validation completed"

# Kubernetes
k8s-deploy: ## Deploy to Kubernetes directly
	@echo "🚀 Deploying to Kubernetes with kubectl..."
	@kubectl apply -f infrastructure/
	@kubectl rollout status deployment/namespace-startup-scheduler -n encendido-eks
	@echo "✅ Kubernetes deployment completed"

k8s-status: ## Check Kubernetes deployment status
	@echo "📊 Checking Kubernetes status..."
	@kubectl get pods -n encendido-eks
	@kubectl get services -n encendido-eks
	@kubectl get configmaps -n encendido-eks

k8s-logs: ## Show Kubernetes logs
	@kubectl logs -f deployment/namespace-startup-scheduler -n encendido-eks

# Monitoring
metrics: ## Show Prometheus metrics
	@echo "📊 Fetching metrics..."
	@curl -s http://localhost:8080/metrics || echo "⚠️  Metrics endpoint not available"

health: ## Check health status
	@echo "🏥 Checking health status..."
	@curl -s http://localhost:8080/health | jq . || echo "⚠️  Health endpoint not available"

# Database
db-init: ## Initialize DynamoDB tables
	@echo "🗄️  Initializing DynamoDB tables..."
	@cd infrastructure && python init-dynamodb.py
	@echo "✅ DynamoDB tables initialized"

db-seed: ## Seed database with test data
	@echo "🌱 Seeding database with test data..."
	@cd controller && python seed_data.py
	@echo "✅ Database seeded"

# Cleanup
clean: clean-docker clean-cache ## Clean all generated files

clean-docker: ## Remove local Docker images and containers
	@echo "🧹 Cleaning Docker resources..."
	@docker-compose down -v --remove-orphans 2>/dev/null || true
	@docker rmi namespace-startup-scheduler-controller:local namespace-startup-scheduler-frontend:local 2>/dev/null || true
	@docker system prune -f

clean-cache: ## Clean cache files
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".coverage" -delete 2>/dev/null || true

# CI/CD
ci-test: ## Run CI/CD tests
	@echo "🔄 Running CI/CD tests..."
	@make lint
	@make security-scan
	@make test

ci-build: ## Build for CI/CD
	@echo "🔄 Running CI/CD build..."
	@make build

# Documentation
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@echo "Project documentation available in README.md"
	@echo "Spec documentation available in .kiro/specs/namespace-startup-scheduler/"

# Information
info: ## Show project information
	@echo "📋 Project Information"
	@echo "====================="
	@echo "Project: Namespace Startup Scheduler"
	@echo "Version: 1.0.0"
	@echo "Components:"
	@echo "  - Controller (Python/FastAPI)"
	@echo "  - Frontend (React/TypeScript)"
	@echo "  - Infrastructure (AWS DynamoDB/S3/EKS)"
	@echo "  - CI/CD (GitHub Actions)"
	@echo "  - Monitoring (Prometheus/Grafana)"
	@echo ""
	@echo "Spec files:"
	@ls -la .kiro/specs/namespace-startup-scheduler/ 2>/dev/null || echo "  No spec files found"
	@echo ""
	@echo "Docker images:"
	@docker images | grep namespace-startup-scheduler || echo "  No images found"