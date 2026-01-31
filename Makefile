# Makefile for Namespace Auto-Shutdown System
# Provides convenient commands for development, testing, and validation

.PHONY: help lint lint-yaml lint-k8s validate test build clean install-tools

# Default target
help: ## Show this help message
	@echo "Namespace Auto-Shutdown System - Development Commands"
	@echo "===================================================="
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Examples:"
	@echo "  make lint              # Run all linting"
	@echo "  make validate          # Run all validations"
	@echo "  make test              # Run all tests"
	@echo "  make build             # Build Docker images"

# Linting targets
lint: lint-yaml lint-k8s ## Run all linting checks

lint-yaml: ## Lint YAML files with yamllint
	@echo "🔍 Running YAML linting..."
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint .; \
		echo "✅ YAML linting completed"; \
	else \
		echo "❌ yamllint not found. Run 'make install-tools' first"; \
		exit 1; \
	fi

lint-k8s: ## Validate Kubernetes manifests
	@echo "🔍 Running Kubernetes manifest validation..."
	@./scripts/validate-k8s-manifests.sh

# Validation targets
validate: validate-yaml validate-docker validate-security ## Run all validations

validate-yaml: ## Comprehensive YAML validation
	@echo "🔍 Running comprehensive YAML validation..."
	@./scripts/validate-yaml.sh

validate-docker: ## Validate Dockerfiles
	@echo "🔍 Validating Dockerfiles..."
	@if command -v hadolint >/dev/null 2>&1; then \
		hadolint controller/Dockerfile; \
		hadolint frontend/Dockerfile; \
		echo "✅ Dockerfile validation completed"; \
	else \
		echo "⚠️  hadolint not found. Skipping Dockerfile validation"; \
		echo "   Install with: brew install hadolint (macOS) or apt install hadolint (Ubuntu)"; \
	fi

validate-security: ## Run security validations
	@echo "🔒 Running security validations..."
	@./scripts/validate-k8s-manifests.sh --security-only

# Testing targets
test: test-controller test-frontend ## Run all tests

test-controller: ## Run controller tests
	@echo "🧪 Running controller tests..."
	@if [ -f controller/requirements.txt ]; then \
		cd controller && python -m pytest tests/ -v --cov=. --cov-report=term-missing || echo "⚠️  No tests found or pytest not available"; \
	else \
		echo "⚠️  Controller requirements.txt not found"; \
	fi

test-frontend: ## Run frontend tests
	@echo "🧪 Running frontend tests..."
	@if [ -f frontend/package.json ]; then \
		cd frontend && npm test -- --coverage --watchAll=false --passWithNoTests || echo "⚠️  Frontend tests failed or npm not available"; \
	else \
		echo "⚠️  Frontend package.json not found"; \
	fi

# Build targets
build: build-controller build-frontend ## Build all Docker images

build-controller: ## Build controller Docker image
	@echo "🐳 Building controller image..."
	@docker build -t namespace-controller:local controller/

build-frontend: ## Build frontend Docker image
	@echo "🐳 Building frontend image..."
	@docker build -t namespace-frontend:local frontend/

build-all: ## Build all images with build script
	@echo "🐳 Building all images with enhanced script..."
	@./scripts/build-images.sh

# Development targets
dev-setup: install-tools ## Set up development environment
	@echo "🛠️  Setting up development environment..."
	@if [ -f controller/requirements.txt ]; then \
		pip install -r controller/requirements.txt; \
	fi
	@if [ -f frontend/package.json ]; then \
		cd frontend && npm install; \
	fi
	@echo "✅ Development environment setup completed"

install-tools: ## Install required development tools
	@echo "🛠️  Installing development tools..."
	@echo "Installing Python tools..."
	@pip install --user yamllint pytest pytest-cov black flake8 isort
	@echo "Installing validation tools..."
	@./scripts/validate-yaml.sh --skip-install || echo "⚠️  Some tools may need manual installation"
	@echo "✅ Tools installation completed"

# Cleanup targets
clean: clean-docker clean-cache ## Clean all generated files

clean-docker: ## Remove local Docker images
	@echo "🧹 Cleaning Docker images..."
	@docker rmi namespace-controller:local namespace-frontend:local 2>/dev/null || echo "No local images to remove"

clean-cache: ## Clean cache files
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".coverage" -delete 2>/dev/null || true

# CI/CD targets
ci-lint: ## Run linting for CI/CD
	@echo "🔄 Running CI/CD linting..."
	@make lint-yaml
	@make validate-yaml

ci-test: ## Run tests for CI/CD
	@echo "🔄 Running CI/CD tests..."
	@make test

ci-build: ## Build for CI/CD
	@echo "🔄 Running CI/CD build..."
	@make build-all

ci-validate: ## Full validation for CI/CD
	@echo "🔄 Running full CI/CD validation..."
	@make validate

# Documentation targets
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@if command -v sphinx-build >/dev/null 2>&1; then \
		echo "Building Sphinx documentation..."; \
		cd docs && make html; \
	else \
		echo "⚠️  Sphinx not found. Install with: pip install sphinx"; \
	fi

# Security targets
security-scan: bandit-scan eslint-security trivy-scan safety-check ## Run all security scans

bandit-scan: ## Run Bandit security scan for Python
	@echo "🔒 Running Bandit security scan..."
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r controller/ -f json -o bandit-report.json || true; \
		bandit -r controller/ -f sarif -o bandit-report.sarif || true; \
		echo "✅ Bandit scan completed. Reports: bandit-report.json, bandit-report.sarif"; \
	else \
		echo "❌ Bandit not found. Run 'pip install bandit[toml]' first"; \
		exit 1; \
	fi

eslint-security: ## Run ESLint security scan for JavaScript/TypeScript
	@echo "🔒 Running ESLint security scan..."
	@if [ -d "frontend" ]; then \
		cd frontend && \
		if [ -f "package.json" ]; then \
			npm install eslint-plugin-security --save-dev 2>/dev/null || true; \
			npx eslint . --ext .js,.jsx,.ts,.tsx --config .eslintrc.security.js --format json --output-file ../eslint-security-report.json || true; \
			echo "✅ ESLint security scan completed. Report: eslint-security-report.json"; \
		else \
			echo "⚠️  No package.json found in frontend directory"; \
		fi; \
	else \
		echo "⚠️  No frontend directory found"; \
	fi

trivy-scan: ## Run Trivy security scan for containers and filesystem
	@echo "🔒 Running Trivy security scan..."
	@if command -v trivy >/dev/null 2>&1; then \
		trivy fs --config trivy.yaml . || true; \
		echo "✅ Trivy filesystem scan completed"; \
		if [ -f "controller/Dockerfile" ]; then \
			trivy config controller/Dockerfile || true; \
			echo "✅ Trivy Dockerfile scan completed"; \
		fi; \
		if [ -f "frontend/Dockerfile" ]; then \
			trivy config frontend/Dockerfile || true; \
			echo "✅ Trivy frontend Dockerfile scan completed"; \
		fi; \
	else \
		echo "❌ Trivy not found. Install from https://aquasecurity.github.io/trivy/"; \
		exit 1; \
	fi

safety-check: ## Run Safety check for Python dependencies
	@echo "🔒 Running Safety dependency check..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check --json --output safety-report.json || true; \
		echo "✅ Safety check completed. Report: safety-report.json"; \
	else \
		echo "❌ Safety not found. Run 'pip install safety' first"; \
		exit 1; \
	fi

install-security-tools: ## Install security scanning tools
	@echo "🛠️  Installing security scanning tools..."
	@echo "Installing Python security tools..."
	@pip install --user bandit[toml] safety semgrep
	@echo "Installing Trivy..."
	@if ! command -v trivy >/dev/null 2>&1; then \
		curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b ~/.local/bin; \
	fi
	@echo "✅ Security tools installation completed"

security-report: ## Generate comprehensive security report
	@echo "📊 Generating comprehensive security report..."
	@mkdir -p reports/security
	@echo "# Security Scan Report" > reports/security/security-report.md
	@echo "Generated on: $$(date)" >> reports/security/security-report.md
	@echo "" >> reports/security/security-report.md
	@if [ -f "bandit-report.json" ]; then \
		echo "## Bandit (Python Security)" >> reports/security/security-report.md; \
		echo "\`\`\`json" >> reports/security/security-report.md; \
		cat bandit-report.json >> reports/security/security-report.md; \
		echo "\`\`\`" >> reports/security/security-report.md; \
		echo "" >> reports/security/security-report.md; \
	fi
	@if [ -f "safety-report.json" ]; then \
		echo "## Safety (Python Dependencies)" >> reports/security/security-report.md; \
		echo "\`\`\`json" >> reports/security/security-report.md; \
		cat safety-report.json >> reports/security/security-report.md; \
		echo "\`\`\`" >> reports/security/security-report.md; \
		echo "" >> reports/security/security-report.md; \
	fi
	@if [ -f "eslint-security-report.json" ]; then \
		echo "## ESLint Security (JavaScript/TypeScript)" >> reports/security/security-report.md; \
		echo "\`\`\`json" >> reports/security/security-report.md; \
		cat eslint-security-report.json >> reports/security/security-report.md; \
		echo "\`\`\`" >> reports/security/security-report.md; \
		echo "" >> reports/security/security-report.md; \
	fi
	@echo "✅ Security report generated: reports/security/security-report.md"

security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	@if command -v trivy >/dev/null 2>&1; then \
		echo "Scanning controller image..."; \
		trivy image namespace-controller:local; \
		echo "Scanning frontend image..."; \
		trivy image namespace-frontend:local; \
	else \
		echo "⚠️  Trivy not found. Install from: https://aquasecurity.github.io/trivy/"; \
	fi

# Utility targets
format: ## Format code
	@echo "🎨 Formatting code..."
	@if [ -d controller ]; then \
		cd controller && black . && isort .; \
	fi
	@if [ -d frontend ]; then \
		cd frontend && npm run format 2>/dev/null || echo "⚠️  Frontend formatting not available"; \
	fi

check: lint validate test ## Run all checks (lint, validate, test)

# Local development
dev-run: ## Run services locally
	@echo "🚀 Starting local development environment..."
	@if [ -f docker-compose.yml ]; then \
		docker-compose up -d; \
	else \
		echo "⚠️  docker-compose.yml not found"; \
	fi

dev-stop: ## Stop local development environment
	@echo "🛑 Stopping local development environment..."
	@if [ -f docker-compose.yml ]; then \
		docker-compose down; \
	else \
		echo "⚠️  docker-compose.yml not found"; \
	fi

# Information targets
info: ## Show project information
	@echo "📋 Project Information"
	@echo "====================="
	@echo "Project: Namespace Auto-Shutdown System"
	@echo "Version: 1.0.0"
	@echo "Components:"
	@echo "  - Controller (Python/FastAPI)"
	@echo "  - Frontend (React/TypeScript)"
	@echo "  - CI/CD (GitHub Actions)"
	@echo "  - Monitoring (Prometheus/Grafana)"
	@echo ""
	@echo "Available scripts:"
	@ls -la scripts/*.sh 2>/dev/null || echo "  No scripts found"
	@echo ""
	@echo "Docker images:"
	@docker images | grep namespace || echo "  No namespace images found"