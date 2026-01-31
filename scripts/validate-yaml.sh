#!/bin/bash
# validate-yaml.sh - Comprehensive YAML validation script
# Validates YAML syntax, Kubernetes manifests, and custom rules

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly TEMP_DIR="/tmp/yaml-validation-$$"
readonly KUBEVAL_VERSION="v0.16.1"
readonly KUSTOMIZE_VERSION="v5.3.0"

# Counters
TOTAL_FILES=0
PASSED_FILES=0
FAILED_FILES=0
WARNINGS=0

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

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT

setup_temp_dir() {
    mkdir -p "$TEMP_DIR"
}

install_tools() {
    log_info "Installing/checking validation tools..."
    
    # Check yamllint
    if ! command -v yamllint &> /dev/null; then
        log_info "Installing yamllint..."
        pip3 install --user yamllint
    fi
    
    # Check/install kubeval
    if ! command -v kubeval &> /dev/null; then
        log_info "Installing kubeval..."
        local kubeval_url="https://github.com/instrumenta/kubeval/releases/download/${KUBEVAL_VERSION}/kubeval-linux-amd64.tar.gz"
        curl -sL "$kubeval_url" | tar xz -C "$TEMP_DIR"
        sudo mv "$TEMP_DIR/kubeval" /usr/local/bin/kubeval
        chmod +x /usr/local/bin/kubeval
    fi
    
    # Check/install kustomize
    if ! command -v kustomize &> /dev/null; then
        log_info "Installing kustomize..."
        local kustomize_url="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_amd64.tar.gz"
        curl -sL "$kustomize_url" | tar xz -C "$TEMP_DIR"
        sudo mv "$TEMP_DIR/kustomize" /usr/local/bin/kustomize
        chmod +x /usr/local/bin/kustomize
    fi
    
    # Check yq for YAML processing
    if ! command -v yq &> /dev/null; then
        log_info "Installing yq..."
        local yq_url="https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64"
        curl -sL "$yq_url" -o "$TEMP_DIR/yq"
        sudo mv "$TEMP_DIR/yq" /usr/local/bin/yq
        chmod +x /usr/local/bin/yq
    fi
    
    log_success "All tools are available"
}

find_yaml_files() {
    local search_path="${1:-.}"
    local exclude_patterns=(
        "node_modules"
        ".git"
        "build"
        "dist"
        "coverage"
        ".vscode"
        ".idea"
        "*.log"
        "*.tmp"
    )
    
    local find_cmd="find '$search_path' -type f \( -name '*.yaml' -o -name '*.yml' \)"
    
    # Add exclude patterns
    for pattern in "${exclude_patterns[@]}"; do
        find_cmd+=" -not -path '*/$pattern/*' -not -name '$pattern'"
    done
    
    eval "$find_cmd" | sort
}

validate_yaml_syntax() {
    local file="$1"
    log_info "Validating YAML syntax: $(basename "$file")"
    
    if yamllint "$file" 2>/dev/null; then
        log_success "YAML syntax valid: $(basename "$file")"
        return 0
    else
        log_error "YAML syntax invalid: $(basename "$file")"
        yamllint "$file" 2>&1 | sed 's/^/  /'
        return 1
    fi
}

validate_kubernetes_manifest() {
    local file="$1"
    local filename=$(basename "$file")
    
    # Skip non-Kubernetes YAML files
    local skip_patterns=(
        ".yamllint.yml"
        "docker-compose"
        "github"
        "gitlab"
        "package.yml"
        "requirements.yml"
    )
    
    for pattern in "${skip_patterns[@]}"; do
        if [[ "$filename" == *"$pattern"* ]]; then
            log_info "Skipping non-Kubernetes file: $filename"
            return 0
        fi
    done
    
    # Check if file contains Kubernetes resources
    if ! grep -q "apiVersion\|kind:" "$file" 2>/dev/null; then
        log_info "Skipping non-Kubernetes YAML: $filename"
        return 0
    fi
    
    log_info "Validating Kubernetes manifest: $filename"
    
    if kubeval --ignore-missing-schemas "$file" 2>/dev/null; then
        log_success "Kubernetes manifest valid: $filename"
        return 0
    else
        log_error "Kubernetes manifest invalid: $filename"
        kubeval --ignore-missing-schemas "$file" 2>&1 | sed 's/^/  /'
        return 1
    fi
}

validate_custom_rules() {
    local file="$1"
    local filename=$(basename "$file")
    local violations=0
    
    log_info "Applying custom validation rules: $filename"
    
    # Rule 1: Check for hardcoded secrets
    if grep -q "password\|secret\|token\|key" "$file" 2>/dev/null; then
        if grep -qE "(password|secret|token|key):\s*['\"]?[a-zA-Z0-9]" "$file" 2>/dev/null; then
            log_warning "Potential hardcoded secret detected in: $filename"
            grep -n -E "(password|secret|token|key):\s*['\"]?[a-zA-Z0-9]" "$file" | sed 's/^/  Line /'
            ((violations++))
        fi
    fi
    
    # Rule 2: Check for missing resource limits in Kubernetes deployments
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$file" 2>/dev/null; then
        if ! grep -q "resources:" "$file" 2>/dev/null; then
            log_warning "Missing resource limits in: $filename"
            ((violations++))
        fi
    fi
    
    # Rule 3: Check for missing labels
    if grep -q "kind: Deployment\|kind: Service\|kind: ConfigMap" "$file" 2>/dev/null; then
        if ! grep -q "labels:" "$file" 2>/dev/null; then
            log_warning "Missing labels in: $filename"
            ((violations++))
        fi
    fi
    
    # Rule 4: Check for latest tag usage
    if grep -q "image:.*:latest" "$file" 2>/dev/null; then
        log_warning "Using 'latest' tag is not recommended in: $filename"
        grep -n "image:.*:latest" "$file" | sed 's/^/  Line /'
        ((violations++))
    fi
    
    # Rule 5: Check for missing security context
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$file" 2>/dev/null; then
        if ! grep -q "securityContext:" "$file" 2>/dev/null; then
            log_warning "Missing security context in: $filename"
            ((violations++))
        fi
    fi
    
    if [ $violations -eq 0 ]; then
        log_success "Custom rules validation passed: $filename"
        return 0
    else
        log_warning "Custom rules validation found $violations issues in: $filename"
        ((WARNINGS += violations))
        return 0  # Don't fail on warnings
    fi
}

validate_kustomization() {
    local dir="$1"
    
    if [ -f "$dir/kustomization.yaml" ] || [ -f "$dir/kustomization.yml" ]; then
        log_info "Validating kustomization in: $(basename "$dir")"
        
        if kustomize build "$dir" > /dev/null 2>&1; then
            log_success "Kustomization valid: $(basename "$dir")"
            return 0
        else
            log_error "Kustomization invalid: $(basename "$dir")"
            kustomize build "$dir" 2>&1 | sed 's/^/  /'
            return 1
        fi
    fi
    
    return 0
}

validate_file() {
    local file="$1"
    local file_passed=true
    
    ((TOTAL_FILES++))
    
    echo ""
    log_info "Processing: $file"
    
    # YAML syntax validation
    if ! validate_yaml_syntax "$file"; then
        file_passed=false
    fi
    
    # Kubernetes manifest validation
    if [ "$file_passed" = true ]; then
        if ! validate_kubernetes_manifest "$file"; then
            file_passed=false
        fi
    fi
    
    # Custom rules validation (warnings only)
    validate_custom_rules "$file"
    
    if [ "$file_passed" = true ]; then
        ((PASSED_FILES++))
        log_success "✓ File validation passed: $(basename "$file")"
    else
        ((FAILED_FILES++))
        log_error "✗ File validation failed: $(basename "$file")"
    fi
    
    return $([[ "$file_passed" = true ]] && echo 0 || echo 1)
}

generate_report() {
    echo ""
    echo "=================================="
    echo "YAML Validation Report"
    echo "=================================="
    echo "Total files processed: $TOTAL_FILES"
    echo "Files passed: $PASSED_FILES"
    echo "Files failed: $FAILED_FILES"
    echo "Warnings: $WARNINGS"
    echo ""
    
    if [ $FAILED_FILES -eq 0 ]; then
        log_success "🎉 All YAML files are valid!"
        if [ $WARNINGS -gt 0 ]; then
            log_warning "Note: $WARNINGS warnings were found (non-blocking)"
        fi
        return 0
    else
        log_error "❌ $FAILED_FILES files failed validation"
        return 1
    fi
}

validate_specific_patterns() {
    log_info "Running pattern-specific validations..."
    
    # Validate GitHub Actions workflows
    if [ -d ".github/workflows" ]; then
        log_info "Validating GitHub Actions workflows..."
        for workflow in .github/workflows/*.{yml,yaml}; do
            if [ -f "$workflow" ]; then
                # Check for required fields in GitHub Actions
                if ! grep -q "on:" "$workflow" 2>/dev/null; then
                    log_warning "Missing 'on:' trigger in workflow: $(basename "$workflow")"
                    ((WARNINGS++))
                fi
                
                if ! grep -q "jobs:" "$workflow" 2>/dev/null; then
                    log_error "Missing 'jobs:' section in workflow: $(basename "$workflow")"
                    ((FAILED_FILES++))
                fi
            fi
        done
    fi
    
    # Validate Docker Compose files
    for compose_file in docker-compose*.{yml,yaml}; do
        if [ -f "$compose_file" ]; then
            log_info "Validating Docker Compose file: $(basename "$compose_file")"
            if command -v docker-compose &> /dev/null; then
                if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
                    log_success "Docker Compose file valid: $(basename "$compose_file")"
                else
                    log_error "Docker Compose file invalid: $(basename "$compose_file")"
                    docker-compose -f "$compose_file" config 2>&1 | sed 's/^/  /'
                    ((FAILED_FILES++))
                fi
            fi
        fi
    done
}

usage() {
    echo "Usage: $0 [OPTIONS] [PATH]"
    echo ""
    echo "Comprehensive YAML validation script"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -f, --fix               Attempt to fix common issues"
    echo "  --skip-install          Skip tool installation"
    echo "  --skip-kubernetes       Skip Kubernetes validation"
    echo "  --skip-custom           Skip custom rules validation"
    echo "  --only-syntax           Only validate YAML syntax"
    echo ""
    echo "Arguments:"
    echo "  PATH                    Path to validate (default: current directory)"
    echo ""
    echo "Examples:"
    echo "  $0                      Validate all YAML files in current directory"
    echo "  $0 controller/          Validate YAML files in controller directory"
    echo "  $0 --only-syntax        Only check YAML syntax"
    echo "  $0 --skip-kubernetes    Skip Kubernetes manifest validation"
}

main() {
    local target_path="."
    local skip_install=false
    local skip_kubernetes=false
    local skip_custom=false
    local only_syntax=false
    local verbose=false
    local fix_issues=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            -f|--fix)
                fix_issues=true
                shift
                ;;
            --skip-install)
                skip_install=true
                shift
                ;;
            --skip-kubernetes)
                skip_kubernetes=true
                shift
                ;;
            --skip-custom)
                skip_custom=true
                shift
                ;;
            --only-syntax)
                only_syntax=true
                shift
                ;;
            -*)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                target_path="$1"
                shift
                ;;
        esac
    done
    
    echo -e "${BLUE}🔍 Comprehensive YAML Validation${NC}"
    echo -e "${BLUE}=================================${NC}"
    echo ""
    
    setup_temp_dir
    
    if [ "$skip_install" = false ]; then
        install_tools
    fi
    
    log_info "Searching for YAML files in: $target_path"
    
    local yaml_files
    mapfile -t yaml_files < <(find_yaml_files "$target_path")
    
    if [ ${#yaml_files[@]} -eq 0 ]; then
        log_warning "No YAML files found in: $target_path"
        exit 0
    fi
    
    log_info "Found ${#yaml_files[@]} YAML files"
    
    # Validate each file
    local overall_result=0
    for file in "${yaml_files[@]}"; do
        if [ "$only_syntax" = true ]; then
            if ! validate_yaml_syntax "$file"; then
                overall_result=1
            fi
        else
            if ! validate_file "$file"; then
                overall_result=1
            fi
        fi
    done
    
    # Run pattern-specific validations
    if [ "$only_syntax" = false ]; then
        validate_specific_patterns
    fi
    
    # Validate kustomizations
    if [ "$skip_kubernetes" = false ] && [ "$only_syntax" = false ]; then
        for dir in $(find "$target_path" -name "kustomization.yaml" -o -name "kustomization.yml" | xargs dirname | sort -u); do
            if ! validate_kustomization "$dir"; then
                overall_result=1
            fi
        done
    fi
    
    generate_report
    
    exit $overall_result
}

# Run main function
main "$@"