#!/bin/bash
# validate-k8s-manifests.sh - Kubernetes manifest validation with security and best practices
# Validates Kubernetes manifests against security policies and best practices

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Counters
TOTAL_MANIFESTS=0
PASSED_MANIFESTS=0
FAILED_MANIFESTS=0
WARNINGS=0
SECURITY_ISSUES=0

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

log_security() {
    echo -e "${RED}🔒 SECURITY: $1${NC}"
}

find_k8s_manifests() {
    local search_path="${1:-.}"
    
    find "$search_path" -type f \( -name "*.yaml" -o -name "*.yml" \) \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/build/*" \
        -not -path "*/dist/*" \
        -not -name ".yamllint.yml" \
        -not -name "docker-compose*.yml" \
        -not -name "docker-compose*.yaml" \
        -exec grep -l "apiVersion\|kind:" {} \; | sort
}

validate_security_context() {
    local file="$1"
    local issues=0
    
    # Check for missing security context
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet\|kind: Pod" "$file"; then
        if ! grep -q "securityContext:" "$file"; then
            log_security "Missing security context in: $(basename "$file")"
            ((issues++))
        else
            # Check for specific security settings
            if ! grep -A 10 "securityContext:" "$file" | grep -q "runAsNonRoot: true"; then
                log_security "Container should run as non-root in: $(basename "$file")"
                ((issues++))
            fi
            
            if ! grep -A 10 "securityContext:" "$file" | grep -q "readOnlyRootFilesystem: true"; then
                log_warning "Consider using read-only root filesystem in: $(basename "$file")"
                ((WARNINGS++))
            fi
            
            if ! grep -A 10 "securityContext:" "$file" | grep -q "allowPrivilegeEscalation: false"; then
                log_security "Should disable privilege escalation in: $(basename "$file")"
                ((issues++))
            fi
        fi
    fi
    
    return $issues
}

validate_resource_limits() {
    local file="$1"
    local issues=0
    
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$file"; then
        if ! grep -q "resources:" "$file"; then
            log_warning "Missing resource limits in: $(basename "$file")"
            ((WARNINGS++))
        else
            # Check for both requests and limits
            if ! grep -A 5 "resources:" "$file" | grep -q "requests:"; then
                log_warning "Missing resource requests in: $(basename "$file")"
                ((WARNINGS++))
            fi
            
            if ! grep -A 5 "resources:" "$file" | grep -q "limits:"; then
                log_warning "Missing resource limits in: $(basename "$file")"
                ((WARNINGS++))
            fi
        fi
    fi
    
    return $issues
}

validate_image_policies() {
    local file="$1"
    local issues=0
    
    # Check for latest tag
    if grep -q "image:.*:latest" "$file"; then
        log_warning "Using 'latest' tag is not recommended in: $(basename "$file")"
        grep -n "image:.*:latest" "$file" | sed 's/^/  Line /'
        ((WARNINGS++))
    fi
    
    # Check for missing image pull policy
    if grep -q "image:" "$file" && ! grep -q "imagePullPolicy:" "$file"; then
        log_warning "Consider specifying imagePullPolicy in: $(basename "$file")"
        ((WARNINGS++))
    fi
    
    # Check for images from untrusted registries
    if grep -qE "image:.*docker\.io|image:.*gcr\.io" "$file"; then
        log_info "Using public registry images in: $(basename "$file")"
    fi
    
    return $issues
}

validate_network_policies() {
    local file="$1"
    local issues=0
    
    # Check if deployment has corresponding network policy
    if grep -q "kind: Deployment" "$file"; then
        local app_name=$(yq eval '.metadata.name' "$file" 2>/dev/null || echo "unknown")
        if [ "$app_name" != "unknown" ] && [ "$app_name" != "null" ]; then
            # Look for network policy in the same directory or project
            local dir=$(dirname "$file")
            if ! find "$dir" -name "*.yaml" -o -name "*.yml" | xargs grep -l "kind: NetworkPolicy" | xargs grep -q "$app_name" 2>/dev/null; then
                log_warning "No NetworkPolicy found for deployment '$app_name' in: $(basename "$file")"
                ((WARNINGS++))
            fi
        fi
    fi
    
    return $issues
}

validate_service_account() {
    local file="$1"
    local issues=0
    
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$file"; then
        if ! grep -q "serviceAccountName:" "$file"; then
            log_warning "Consider specifying serviceAccountName in: $(basename "$file")"
            ((WARNINGS++))
        fi
    fi
    
    # Check for service account with automountServiceAccountToken
    if grep -q "kind: ServiceAccount" "$file"; then
        if ! grep -q "automountServiceAccountToken: false" "$file"; then
            log_security "ServiceAccount should disable token automounting unless needed in: $(basename "$file")"
            ((issues++))
        fi
    fi
    
    return $issues
}

validate_secrets_management() {
    local file="$1"
    local issues=0
    
    # Check for hardcoded secrets
    if grep -qE "(password|secret|token|key|api_key):\s*['\"]?[a-zA-Z0-9]" "$file"; then
        log_security "Potential hardcoded secret detected in: $(basename "$file")"
        grep -nE "(password|secret|token|key|api_key):\s*['\"]?[a-zA-Z0-9]" "$file" | sed 's/^/  Line /'
        ((issues++))
    fi
    
    # Check for base64 encoded values that might be secrets
    if grep -qE "['\"][A-Za-z0-9+/]{20,}={0,2}['\"]" "$file"; then
        log_warning "Potential base64 encoded secret in: $(basename "$file")"
        ((WARNINGS++))
    fi
    
    return $issues
}

validate_labels_and_annotations() {
    local file="$1"
    local issues=0
    
    # Required labels for proper resource management
    local required_labels=("app" "version" "component")
    
    if grep -q "kind: Deployment\|kind: Service\|kind: ConfigMap\|kind: Secret" "$file"; then
        if ! grep -q "labels:" "$file"; then
            log_warning "Missing labels in: $(basename "$file")"
            ((WARNINGS++))
        else
            # Check for specific required labels
            for label in "${required_labels[@]}"; do
                if ! grep -A 10 "labels:" "$file" | grep -q "$label:"; then
                    log_info "Consider adding '$label' label in: $(basename "$file")"
                fi
            done
        fi
    fi
    
    return $issues
}

validate_probes() {
    local file="$1"
    local issues=0
    
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$file"; then
        if ! grep -q "livenessProbe:" "$file"; then
            log_warning "Missing liveness probe in: $(basename "$file")"
            ((WARNINGS++))
        fi
        
        if ! grep -q "readinessProbe:" "$file"; then
            log_warning "Missing readiness probe in: $(basename "$file")"
            ((WARNINGS++))
        fi
    fi
    
    return $issues
}

validate_rbac() {
    local file="$1"
    local issues=0
    
    # Check for overly permissive RBAC
    if grep -q "kind: ClusterRole\|kind: Role" "$file"; then
        if grep -q "resources: \[\"\\*\"\]\|verbs: \[\"\\*\"\]" "$file"; then
            log_security "Overly permissive RBAC detected in: $(basename "$file")"
            ((issues++))
        fi
    fi
    
    return $issues
}

validate_pod_security_standards() {
    local file="$1"
    local issues=0
    
    if grep -q "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet\|kind: Pod" "$file"; then
        # Check for privileged containers
        if grep -q "privileged: true" "$file"; then
            log_security "Privileged container detected in: $(basename "$file")"
            ((issues++))
        fi
        
        # Check for host network
        if grep -q "hostNetwork: true" "$file"; then
            log_security "Host network usage detected in: $(basename "$file")"
            ((issues++))
        fi
        
        # Check for host PID
        if grep -q "hostPID: true" "$file"; then
            log_security "Host PID usage detected in: $(basename "$file")"
            ((issues++))
        fi
        
        # Check for host IPC
        if grep -q "hostIPC: true" "$file"; then
            log_security "Host IPC usage detected in: $(basename "$file")"
            ((issues++))
        fi
    fi
    
    return $issues
}

validate_manifest() {
    local file="$1"
    local manifest_issues=0
    
    ((TOTAL_MANIFESTS++))
    
    echo ""
    log_info "Validating Kubernetes manifest: $(basename "$file")"
    
    # Security validations
    validate_security_context "$file"
    manifest_issues=$((manifest_issues + $?))
    
    validate_service_account "$file"
    manifest_issues=$((manifest_issues + $?))
    
    validate_secrets_management "$file"
    manifest_issues=$((manifest_issues + $?))
    
    validate_rbac "$file"
    manifest_issues=$((manifest_issues + $?))
    
    validate_pod_security_standards "$file"
    manifest_issues=$((manifest_issues + $?))
    
    # Best practices validations (warnings only)
    validate_resource_limits "$file"
    validate_image_policies "$file"
    validate_network_policies "$file"
    validate_labels_and_annotations "$file"
    validate_probes "$file"
    
    if [ $manifest_issues -eq 0 ]; then
        ((PASSED_MANIFESTS++))
        log_success "✓ Manifest validation passed: $(basename "$file")"
    else
        ((FAILED_MANIFESTS++))
        ((SECURITY_ISSUES += manifest_issues))
        log_error "✗ Manifest validation failed: $(basename "$file") ($manifest_issues security issues)"
    fi
    
    return $manifest_issues
}

generate_security_report() {
    echo ""
    echo "========================================"
    echo "Kubernetes Security Validation Report"
    echo "========================================"
    echo "Total manifests processed: $TOTAL_MANIFESTS"
    echo "Manifests passed: $PASSED_MANIFESTS"
    echo "Manifests failed: $FAILED_MANIFESTS"
    echo "Security issues: $SECURITY_ISSUES"
    echo "Warnings: $WARNINGS"
    echo ""
    
    if [ $SECURITY_ISSUES -eq 0 ]; then
        log_success "🔒 No security issues found!"
        if [ $WARNINGS -gt 0 ]; then
            log_warning "Note: $WARNINGS best practice warnings were found"
        fi
        return 0
    else
        log_error "🚨 $SECURITY_ISSUES security issues found that need attention"
        return 1
    fi
}

usage() {
    echo "Usage: $0 [OPTIONS] [PATH]"
    echo ""
    echo "Kubernetes manifest security and best practices validation"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -v, --verbose           Enable verbose output"
    echo "  --security-only         Only run security validations"
    echo "  --no-warnings           Don't show warnings, only errors"
    echo ""
    echo "Arguments:"
    echo "  PATH                    Path to validate (default: current directory)"
    echo ""
    echo "Examples:"
    echo "  $0                      Validate all manifests in current directory"
    echo "  $0 controller/          Validate manifests in controller directory"
    echo "  $0 --security-only      Only run security validations"
}

main() {
    local target_path="."
    local security_only=false
    local no_warnings=false
    local verbose=false
    
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
            --security-only)
                security_only=true
                shift
                ;;
            --no-warnings)
                no_warnings=true
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
    
    echo -e "${BLUE}🔒 Kubernetes Security Validation${NC}"
    echo -e "${BLUE}==================================${NC}"
    echo ""
    
    log_info "Searching for Kubernetes manifests in: $target_path"
    
    local k8s_files
    mapfile -t k8s_files < <(find_k8s_manifests "$target_path")
    
    if [ ${#k8s_files[@]} -eq 0 ]; then
        log_warning "No Kubernetes manifests found in: $target_path"
        exit 0
    fi
    
    log_info "Found ${#k8s_files[@]} Kubernetes manifests"
    
    # Validate each manifest
    local overall_result=0
    for file in "${k8s_files[@]}"; do
        if ! validate_manifest "$file"; then
            overall_result=1
        fi
    done
    
    generate_security_report
    
    exit $overall_result
}

# Run main function
main "$@"