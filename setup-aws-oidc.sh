#!/bin/bash
# setup-aws-oidc.sh - Enhanced script for configuring OIDC with GitHub Actions
# Supports namespace auto-shutdown system with enhanced security

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly OIDC_PROVIDER_URL="token.actions.githubusercontent.com"
readonly OIDC_THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"
readonly ROLE_NAME="GitHubActionsNamespaceControllerRole"
readonly POLICY_NAME="NamespaceControllerECRPolicy"
readonly ROLE_SESSION_DURATION=3600  # 1 hour

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
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI is not configured or you don't have permissions"
        echo "Run: aws configure"
        exit 1
    fi
    
    # Check jq for JSON processing
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed. Installing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v yum &> /dev/null; then
            sudo yum install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        else
            log_error "Cannot install jq automatically. Please install it manually."
            exit 1
        fi
    fi
    
    log_success "Prerequisites check completed"
}

get_aws_info() {
    log_info "Gathering AWS account information..."
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}
    CALLER_IDENTITY=$(aws sts get-caller-identity)
    
    echo -e "${YELLOW}📋 AWS Configuration:${NC}"
    echo "Account ID: $ACCOUNT_ID"
    echo "Region: $AWS_REGION"
    echo "Current User/Role: $(echo "$CALLER_IDENTITY" | jq -r '.Arn')"
    echo ""
}

get_github_repo() {
    log_info "GitHub repository configuration..."
    
    # Try to detect from git remote
    if git remote get-url origin &> /dev/null; then
        GIT_REMOTE=$(git remote get-url origin)
        if [[ $GIT_REMOTE =~ github\.com[:/]([^/]+/[^/]+) ]]; then
            DETECTED_REPO="${BASH_REMATCH[1]}"
            DETECTED_REPO="${DETECTED_REPO%.git}"  # Remove .git suffix
            log_info "Detected repository: $DETECTED_REPO"
            read -p "Use detected repository '$DETECTED_REPO'? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                GITHUB_REPO="$DETECTED_REPO"
                return
            fi
        fi
    fi
    
    # Manual input
    while [[ -z "${GITHUB_REPO:-}" ]]; do
        read -p "🔗 Enter your GitHub repository (format: username/repo): " GITHUB_REPO
        if [[ ! $GITHUB_REPO =~ ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$ ]]; then
            log_error "Invalid repository format. Use: username/repository"
            GITHUB_REPO=""
        fi
    done
}

create_oidc_provider() {
    log_info "Creating OIDC Identity Provider..."
    
    local provider_arn="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER_URL}"
    
    if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$provider_arn" &> /dev/null; then
        log_warning "OIDC Provider already exists"
    else
        aws iam create-open-id-connect-provider \
            --url "https://${OIDC_PROVIDER_URL}" \
            --client-id-list sts.amazonaws.com \
            --thumbprint-list "$OIDC_THUMBPRINT" \
            --tags Key=Purpose,Value=GitHubActions Key=Project,Value=NamespaceAutoShutdown
        log_success "OIDC Provider created"
    fi
}

create_ecr_policy() {
    log_info "Creating enhanced ECR policy..."
    
    local policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
    
    cat > /tmp/ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRAuthToken",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "ECRRepositoryAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchImportLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:DescribeRepositories",
                "ecr:DescribeImages",
                "ecr:InitiateLayerUpload",
                "ecr:PutImage",
                "ecr:UploadLayerPart",
                "ecr:ListImages"
            ],
            "Resource": [
                "arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/namespace-scaler",
                "arn:aws:ecr:${AWS_REGION}:${ACCOUNT_ID}:repository/namespace-frontend"
            ]
        }
    ]
}
EOF

    if aws iam get-policy --policy-arn "$policy_arn" &> /dev/null; then
        log_warning "ECR Policy already exists, updating..."
        aws iam create-policy-version \
            --policy-arn "$policy_arn" \
            --policy-document file:///tmp/ecr-policy.json \
            --set-as-default
        log_success "ECR Policy updated"
    else
        aws iam create-policy \
            --policy-name "$POLICY_NAME" \
            --policy-document file:///tmp/ecr-policy.json \
            --description "Enhanced ECR access policy for namespace auto-shutdown system" \
            --tags Key=Purpose,Value=GitHubActions Key=Project,Value=NamespaceAutoShutdown
        log_success "ECR Policy created"
    fi
}

create_trust_policy() {
    log_info "Creating enhanced trust policy..."
    
    cat > /tmp/trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER_URL}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "${OIDC_PROVIDER_URL}:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "${OIDC_PROVIDER_URL}:sub": [
                        "repo:${GITHUB_REPO}:ref:refs/heads/main",
                        "repo:${GITHUB_REPO}:ref:refs/heads/develop",
                        "repo:${GITHUB_REPO}:pull_request"
                    ]
                }
            }
        }
    ]
}
EOF
}

create_iam_role() {
    log_info "Creating enhanced IAM Role..."
    
    local role_arn="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
    
    if aws iam get-role --role-name "$ROLE_NAME" &> /dev/null; then
        log_warning "IAM Role already exists, updating trust policy..."
        aws iam update-assume-role-policy \
            --role-name "$ROLE_NAME" \
            --policy-document file:///tmp/trust-policy.json
        log_success "IAM Role trust policy updated"
    else
        aws iam create-role \
            --role-name "$ROLE_NAME" \
            --assume-role-policy-document file:///tmp/trust-policy.json \
            --description "Enhanced IAM role for namespace auto-shutdown system GitHub Actions" \
            --max-session-duration "$ROLE_SESSION_DURATION" \
            --tags Key=Purpose,Value=GitHubActions Key=Project,Value=NamespaceAutoShutdown
        log_success "IAM Role created"
    fi
}

attach_policies() {
    log_info "Attaching policies to IAM role..."
    
    local policy_arn="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"
    
    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "$policy_arn"
    
    log_success "Policies attached to role"
}

create_ecr_repositories() {
    log_info "Creating ECR repositories..."
    
    local repositories=("namespace-scaler" "namespace-frontend")
    
    for repo in "${repositories[@]}"; do
        if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" &> /dev/null; then
            log_warning "Repository $repo already exists"
        else
            aws ecr create-repository \
                --repository-name "$repo" \
                --region "$AWS_REGION" \
                --image-scanning-configuration scanOnPush=true \
                --encryption-configuration encryptionType=AES256 \
                --tags Key=Purpose,Value=NamespaceAutoShutdown Key=Component,Value="$repo"
            log_success "Repository $repo created"
        fi
        
        # Set lifecycle policy
        cat > /tmp/lifecycle-policy.json << EOF
{
    "rules": [
        {
            "rulePriority": 1,
            "description": "Keep last 10 images",
            "selection": {
                "tagStatus": "tagged",
                "countType": "imageCountMoreThan",
                "countNumber": 10
            },
            "action": {
                "type": "expire"
            }
        },
        {
            "rulePriority": 2,
            "description": "Delete untagged images older than 1 day",
            "selection": {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "days",
                "countNumber": 1
            },
            "action": {
                "type": "expire"
            }
        }
    ]
}
EOF
        
        aws ecr put-lifecycle-policy \
            --repository-name "$repo" \
            --region "$AWS_REGION" \
            --lifecycle-policy-text file:///tmp/lifecycle-policy.json &> /dev/null || true
    done
}

cleanup_temp_files() {
    rm -f /tmp/ecr-policy.json /tmp/trust-policy.json /tmp/lifecycle-policy.json
}

print_summary() {
    local role_arn="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
    
    echo ""
    log_success "🎉 OIDC setup completed successfully!"
    echo ""
    echo -e "${YELLOW}📋 CONFIGURATION SUMMARY:${NC}"
    echo -e "${BLUE}AWS Account ID:${NC} $ACCOUNT_ID"
    echo -e "${BLUE}AWS Region:${NC} $AWS_REGION"
    echo -e "${BLUE}GitHub Repository:${NC} $GITHUB_REPO"
    echo -e "${BLUE}IAM Role ARN:${NC} $role_arn"
    echo ""
    echo -e "${YELLOW}🔧 NEXT STEPS:${NC}"
    echo "1. Go to your GitHub repository: https://github.com/${GITHUB_REPO}"
    echo "2. Navigate to Settings → Secrets and variables → Actions"
    echo "3. Click 'New repository secret'"
    echo "4. Add this secret:"
    echo -e "   ${BLUE}Name:${NC} AWS_ROLE_ARN"
    echo -e "   ${BLUE}Value:${NC} $role_arn"
    echo ""
    echo -e "${YELLOW}📦 ECR REPOSITORIES:${NC}"
    echo "• ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-scaler"
    echo "• ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/namespace-frontend"
    echo ""
    echo -e "${YELLOW}🔒 SECURITY FEATURES:${NC}"
    echo "• OIDC authentication (no long-term credentials)"
    echo "• Repository-specific access restrictions"
    echo "• Enhanced ECR permissions with least privilege"
    echo "• Image scanning enabled on push"
    echo "• Lifecycle policies for cost optimization"
    echo ""
    echo -e "${GREEN}✅ Ready to use GitHub Actions with enhanced OIDC security!${NC}"
}

main() {
    echo -e "${BLUE}🚀 Enhanced OIDC Setup for Namespace Auto-Shutdown System${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
    
    check_prerequisites
    get_aws_info
    get_github_repo
    
    echo ""
    log_info "Starting OIDC configuration..."
    
    create_oidc_provider
    create_ecr_policy
    create_trust_policy
    create_iam_role
    attach_policies
    create_ecr_repositories
    cleanup_temp_files
    
    print_summary
}

# Run main function
main "$@"