#!/bin/bash
# build-images.sh - Script to build and validate Docker images locally

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
readonly CONTROLLER_DIR="$PROJECT_ROOT/controller"
readonly FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Image names
readonly CONTROLLER_IMAGE="namespace-controller:local"
readonly FRONTEND_IMAGE="namespace-frontend:local"

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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check buildx (for multi-platform builds)
    if ! docker buildx version &> /dev/null; then
        log_warning "Docker buildx not available, using regular build"
        USE_BUILDX=false
    else
        USE_BUILDX=true
    fi
    
    log_success "Prerequisites check completed"
}

build_controller() {
    log_info "Building controller image..."
    
    cd "$CONTROLLER_DIR"
    
    if [ "$USE_BUILDX" = true ]; then
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --tag "$CONTROLLER_IMAGE" \
            --load \
            .
    else
        docker build \
            --tag "$CONTROLLER_IMAGE" \
            .
    fi
    
    log_success "Controller image built successfully"
}

build_frontend() {
    log_info "Building frontend image..."
    
    cd "$FRONTEND_DIR"
    
    if [ "$USE_BUILDX" = true ]; then
        docker buildx build \
            --platform linux/amd64,linux/arm64 \
            --tag "$FRONTEND_IMAGE" \
            --load \
            .
    else
        docker build \
            --tag "$FRONTEND_IMAGE" \
            .
    fi
    
    log_success "Frontend image built successfully"
}

validate_images() {
    log_info "Validating built images..."
    
    # Check controller image
    log_info "Validating controller image..."
    if docker run --rm "$CONTROLLER_IMAGE" python --version; then
        log_success "Controller image validation passed"
    else
        log_error "Controller image validation failed"
        return 1
    fi
    
    # Check frontend image
    log_info "Validating frontend image..."
    if docker run --rm "$FRONTEND_IMAGE" nginx -t; then
        log_success "Frontend image validation passed"
    else
        log_error "Frontend image validation failed"
        return 1
    fi
}

scan_security() {
    log_info "Scanning images for security vulnerabilities..."
    
    # Check if trivy is available
    if command -v trivy &> /dev/null; then
        log_info "Scanning controller image with Trivy..."
        trivy image --severity HIGH,CRITICAL "$CONTROLLER_IMAGE" || log_warning "Controller image has vulnerabilities"
        
        log_info "Scanning frontend image with Trivy..."
        trivy image --severity HIGH,CRITICAL "$FRONTEND_IMAGE" || log_warning "Frontend image has vulnerabilities"
    else
        log_warning "Trivy not found, skipping security scan"
        log_info "Install Trivy for security scanning: https://aquasecurity.github.io/trivy/"
    fi
}

show_image_info() {
    log_info "Image information:"
    
    echo -e "${BLUE}Controller Image:${NC}"
    docker images "$CONTROLLER_IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    echo -e "${BLUE}Frontend Image:${NC}"
    docker images "$FRONTEND_IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
}

cleanup() {
    if [ "${CLEANUP:-false}" = true ]; then
        log_info "Cleaning up images..."
        docker rmi "$CONTROLLER_IMAGE" "$FRONTEND_IMAGE" 2>/dev/null || true
        log_success "Cleanup completed"
    fi
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --controller-only    Build only controller image"
    echo "  -f, --frontend-only      Build only frontend image"
    echo "  -s, --skip-security      Skip security scanning"
    echo "  -v, --skip-validation    Skip image validation"
    echo "  --cleanup               Remove images after build"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      Build both images"
    echo "  $0 -c                   Build only controller"
    echo "  $0 -f --skip-security   Build only frontend, skip security scan"
}

main() {
    local build_controller=true
    local build_frontend=true
    local skip_security=false
    local skip_validation=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--controller-only)
                build_frontend=false
                shift
                ;;
            -f|--frontend-only)
                build_controller=false
                shift
                ;;
            -s|--skip-security)
                skip_security=true
                shift
                ;;
            -v|--skip-validation)
                skip_validation=true
                shift
                ;;
            --cleanup)
                CLEANUP=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    echo -e "${BLUE}🐳 Building Docker Images for Namespace Auto-Shutdown System${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
    
    check_prerequisites
    
    # Build images
    if [ "$build_controller" = true ]; then
        build_controller
    fi
    
    if [ "$build_frontend" = true ]; then
        build_frontend
    fi
    
    # Validate images
    if [ "$skip_validation" = false ]; then
        validate_images
    fi
    
    # Security scanning
    if [ "$skip_security" = false ]; then
        scan_security
    fi
    
    show_image_info
    
    echo ""
    log_success "🎉 Build process completed successfully!"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Test the images locally with docker-compose"
    echo "2. Push to your container registry"
    echo "3. Deploy to your Kubernetes cluster"
    echo ""
    echo -e "${BLUE}Local testing:${NC}"
    echo "  docker run --rm -p 8080:8080 $CONTROLLER_IMAGE"
    echo "  docker run --rm -p 3000:8080 $FRONTEND_IMAGE"
}

# Set up cleanup trap
trap cleanup EXIT

# Run main function
main "$@"