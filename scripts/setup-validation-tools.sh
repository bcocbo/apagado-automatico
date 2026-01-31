#!/bin/bash
# setup-validation-tools.sh - Install and configure all validation tools
# Sets up yamllint, kubeval, hadolint, and other validation tools

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Tool versions
readonly KUBEVAL_VERSION="v0.16.1"
readonly KUSTOMIZE_VERSION="v5.3.0"
readonly HADOLINT_VERSION="v2.12.0"
readonly YQ_VERSION="v4.40.5"
readonly TRIVY_VERSION="v0.48.3"

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "darwin"
    else
        echo "unknown"
    fi
}

detect_arch() {
    local arch=$(uname -m)
    case $arch in
        x86_64) echo "amd64" ;;
        arm64|aarch64) echo "arm64" ;;
        *) echo "amd64" ;;
    esac
}

install_python_tools() {
    log_info "Installing Python validation tools..."
    
    # Check if pip is available
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        log_error "pip not found. Please install Python and pip first."
        return 1
    fi
    
    local pip_cmd="pip3"
    if ! command -v pip3 &> /dev/null; then
        pip_cmd="pip"
    fi
    
    # Install Python tools
    local python_tools=(
        "yamllint>=1.35.0"
        "pytest>=8.0.0"
        "pytest-cov>=4.1.0"
        "black>=24.0.0"
        "flake8>=7.0.0"
        "isort>=5.13.0"
        "pre-commit>=3.6.0"
    )
    
    for tool in "${python_tools[@]}"; do
        log_info "Installing $tool..."
        $pip_cmd install --user "$tool" || log_warning "Failed to install $tool"
    done
    
    log_success "Python tools installation completed"
}

install_kubeval() {
    log_info "Installing kubeval..."
    
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system for kubeval"
        return 1
    fi
    
    local kubeval_url="https://github.com/instrumenta/kubeval/releases/download/${KUBEVAL_VERSION}/kubeval-${os}-${arch}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    curl -sL "$kubeval_url" | tar xz -C "$temp_dir"
    
    if [[ -f "$temp_dir/kubeval" ]]; then
        sudo mv "$temp_dir/kubeval" /usr/local/bin/kubeval
        chmod +x /usr/local/bin/kubeval
        log_success "kubeval installed successfully"
    else
        log_error "Failed to install kubeval"
        return 1
    fi
    
    rm -rf "$temp_dir"
}

install_kustomize() {
    log_info "Installing kustomize..."
    
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system for kustomize"
        return 1
    fi
    
    local kustomize_url="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_${os}_${arch}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    curl -sL "$kustomize_url" | tar xz -C "$temp_dir"
    
    if [[ -f "$temp_dir/kustomize" ]]; then
        sudo mv "$temp_dir/kustomize" /usr/local/bin/kustomize
        chmod +x /usr/local/bin/kustomize
        log_success "kustomize installed successfully"
    else
        log_error "Failed to install kustomize"
        return 1
    fi
    
    rm -rf "$temp_dir"
}

install_hadolint() {
    log_info "Installing hadolint..."
    
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system for hadolint"
        return 1
    fi
    
    # Hadolint uses different naming convention
    local hadolint_os="Linux"
    if [[ "$os" == "darwin" ]]; then
        hadolint_os="Darwin"
    fi
    
    local hadolint_arch="x86_64"
    if [[ "$arch" == "arm64" ]]; then
        hadolint_arch="arm64"
    fi
    
    local hadolint_url="https://github.com/hadolint/hadolint/releases/download/${HADOLINT_VERSION}/hadolint-${hadolint_os}-${hadolint_arch}"
    
    curl -sL "$hadolint_url" -o /tmp/hadolint
    
    if [[ -f "/tmp/hadolint" ]]; then
        sudo mv /tmp/hadolint /usr/local/bin/hadolint
        chmod +x /usr/local/bin/hadolint
        log_success "hadolint installed successfully"
    else
        log_error "Failed to install hadolint"
        return 1
    fi
}

install_yq() {
    log_info "Installing yq..."
    
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system for yq"
        return 1
    fi
    
    local yq_url="https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_${os}_${arch}"
    
    curl -sL "$yq_url" -o /tmp/yq
    
    if [[ -f "/tmp/yq" ]]; then
        sudo mv /tmp/yq /usr/local/bin/yq
        chmod +x /usr/local/bin/yq
        log_success "yq installed successfully"
    else
        log_error "Failed to install yq"
        return 1
    fi
}

install_trivy() {
    log_info "Installing trivy..."
    
    local os=$(detect_os)
    local arch=$(detect_arch)
    
    if [[ "$os" == "unknown" ]]; then
        log_error "Unsupported operating system for trivy"
        return 1
    fi
    
    # Trivy uses different naming
    local trivy_os="Linux"
    if [[ "$os" == "darwin" ]]; then
        trivy_os="macOS"
    fi
    
    local trivy_arch="64bit"
    if [[ "$arch" == "arm64" ]]; then
        trivy_arch="ARM64"
    fi
    
    local trivy_url="https://github.com/aquasecurity/trivy/releases/download/${TRIVY_VERSION}/trivy_${TRIVY_VERSION#v}_${trivy_os}-${trivy_arch}.tar.gz"
    local temp_dir=$(mktemp -d)
    
    curl -sL "$trivy_url" | tar xz -C "$temp_dir"
    
    if [[ -f "$temp_dir/trivy" ]]; then
        sudo mv "$temp_dir/trivy" /usr/local/bin/trivy
        chmod +x /usr/local/bin/trivy
        log_success "trivy installed successfully"
    else
        log_error "Failed to install trivy"
        return 1
    fi
    
    rm -rf "$temp_dir"
}

install_node_tools() {
    log_info "Installing Node.js validation tools..."
    
    if ! command -v npm &> /dev/null; then
        log_warning "npm not found. Skipping Node.js tools installation."
        return 0
    fi
    
    # Global tools
    local node_tools=(
        "eslint"
        "@typescript-eslint/parser"
        "@typescript-eslint/eslint-plugin"
        "prettier"
    )
    
    for tool in "${node_tools[@]}"; do
        log_info "Installing $tool..."
        npm install -g "$tool" || log_warning "Failed to install $tool"
    done
    
    log_success "Node.js tools installation completed"
}

setup_pre_commit() {
    log_info "Setting up pre-commit hooks..."
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        pre-commit install --hook-type commit-msg
        log_success "Pre-commit hooks installed"
    else
        log_warning "pre-commit not found. Install with: pip install pre-commit"
    fi
}

verify_installations() {
    log_info "Verifying tool installations..."
    
    local tools=(
        "yamllint --version"
        "kubeval --version"
        "kustomize version"
        "hadolint --version"
        "yq --version"
        "trivy --version"
        "black --version"
        "flake8 --version"
        "pytest --version"
    )
    
    local failed_tools=()
    
    for tool_cmd in "${tools[@]}"; do
        local tool_name=$(echo "$tool_cmd" | cut -d' ' -f1)
        if $tool_cmd &> /dev/null; then
            log_success "$tool_name is working"
        else
            log_error "$tool_name is not working"
            failed_tools+=("$tool_name")
        fi
    done
    
    if [ ${#failed_tools[@]} -eq 0 ]; then
        log_success "All tools are working correctly!"
        return 0
    else
        log_error "The following tools failed verification: ${failed_tools[*]}"
        return 1
    fi
}

create_validation_config() {
    log_info "Creating validation configuration files..."
    
    # Create hadolint config if it doesn't exist
    if [[ ! -f ".hadolint.yaml" ]]; then
        cat > .hadolint.yaml << 'EOF'
# Hadolint configuration for Dockerfile linting
ignored:
  - DL3008  # Pin versions in apt get install
  - DL3009  # Delete the apt-get lists after installing something
  - DL3015  # Avoid additional packages by specifying --no-install-recommends

trustedRegistries:
  - docker.io
  - gcr.io
  - quay.io

allowedRegistries:
  - docker.io
  - gcr.io
  - quay.io
  - your-registry.com
EOF
        log_success "Created .hadolint.yaml"
    fi
    
    # Create secrets baseline if it doesn't exist
    if [[ ! -f ".secrets.baseline" ]]; then
        echo '{}' > .secrets.baseline
        log_success "Created .secrets.baseline"
    fi
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Install and configure validation tools for the namespace auto-shutdown system"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  --skip-python           Skip Python tools installation"
    echo "  --skip-node             Skip Node.js tools installation"
    echo "  --skip-binary           Skip binary tools installation"
    echo "  --verify-only           Only verify existing installations"
    echo ""
    echo "Examples:"
    echo "  $0                      Install all tools"
    echo "  $0 --skip-node          Install all except Node.js tools"
    echo "  $0 --verify-only        Only verify existing tools"
}

main() {
    local skip_python=false
    local skip_node=false
    local skip_binary=false
    local verify_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            --skip-python)
                skip_python=true
                shift
                ;;
            --skip-node)
                skip_node=true
                shift
                ;;
            --skip-binary)
                skip_binary=true
                shift
                ;;
            --verify-only)
                verify_only=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    echo -e "${BLUE}🛠️  Validation Tools Setup${NC}"
    echo -e "${BLUE}==========================${NC}"
    echo ""
    
    if [[ "$verify_only" == "true" ]]; then
        verify_installations
        exit $?
    fi
    
    # Install tools
    if [[ "$skip_python" == "false" ]]; then
        install_python_tools
    fi
    
    if [[ "$skip_binary" == "false" ]]; then
        install_kubeval
        install_kustomize
        install_hadolint
        install_yq
        install_trivy
    fi
    
    if [[ "$skip_node" == "false" ]]; then
        install_node_tools
    fi
    
    create_validation_config
    setup_pre_commit
    
    echo ""
    verify_installations
    
    echo ""
    log_success "🎉 Validation tools setup completed!"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Run 'make lint' to validate YAML files"
    echo "2. Run 'make validate' for comprehensive validation"
    echo "3. Run 'pre-commit run --all-files' to test pre-commit hooks"
    echo ""
    echo -e "${BLUE}Available commands:${NC}"
    echo "  make lint              # Run all linting"
    echo "  make validate          # Run all validations"
    echo "  make validate-security # Run security validations"
    echo "  ./scripts/validate-yaml.sh # Comprehensive YAML validation"
}

# Run main function
main "$@"