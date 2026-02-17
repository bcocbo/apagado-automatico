#!/bin/bash

# Script para probar permisos RBAC del kubectl-runner
# Este script debe ejecutarse desde un pod que use el ServiceAccount kubectl-runner

set -e

echo "=========================================="
echo "Testing kubectl-runner RBAC Permissions"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Function to test a command
test_command() {
    local description="$1"
    local command="$2"
    local should_succeed="$3"
    
    echo -n "Testing: $description ... "
    
    if eval "$command" &> /dev/null; then
        if [ "$should_succeed" = "true" ]; then
            echo -e "${GREEN}✓ PASSED${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ FAILED (should have been denied)${NC}"
            ((FAILED++))
        fi
    else
        if [ "$should_succeed" = "false" ]; then
            echo -e "${GREEN}✓ PASSED (correctly denied)${NC}"
            ((PASSED++))
        else
            echo -e "${RED}✗ FAILED (should have succeeded)${NC}"
            ((FAILED++))
        fi
    fi
}

echo "=== 1. Testing Namespace Permissions ==="
test_command "List namespaces" "kubectl get namespaces" "true"
test_command "Get specific namespace" "kubectl get namespace default" "true"
test_command "Create namespace (should fail)" "kubectl create namespace test-rbac-temp" "false"
test_command "Delete namespace (should fail)" "kubectl delete namespace test-rbac-temp" "false"
echo ""

echo "=== 2. Testing Pod Read Permissions ==="
test_command "List pods in all namespaces" "kubectl get pods --all-namespaces" "true"
test_command "List pods in default namespace" "kubectl get pods -n default" "true"
test_command "List pods in kube-system" "kubectl get pods -n kube-system" "true"
echo ""

echo "=== 3. Testing Deployment Read Permissions ==="
test_command "List deployments in all namespaces" "kubectl get deployments --all-namespaces" "true"
test_command "Get deployment details" "kubectl get deployment -n task-scheduler task-scheduler-backend -o yaml" "true"
echo ""

echo "=== 4. Testing StatefulSet Read Permissions ==="
test_command "List statefulsets in all namespaces" "kubectl get statefulsets --all-namespaces" "true"
echo ""

echo "=== 5. Testing Scale Permissions in Non-Protected Namespaces ==="
# First, check if there's a test namespace we can use
if kubectl get namespace test-namespace &> /dev/null; then
    test_command "Get deployment scale in test-namespace" "kubectl get deployment -n test-namespace --no-headers 2>/dev/null | head -1 | awk '{print \$1}' | xargs -I {} kubectl get deployment/{} -n test-namespace" "true"
    
    # Try to scale if deployment exists
    DEPLOY=$(kubectl get deployment -n test-namespace --no-headers 2>/dev/null | head -1 | awk '{print $1}')
    if [ ! -z "$DEPLOY" ]; then
        test_command "Scale deployment in test-namespace" "kubectl scale deployment/$DEPLOY -n test-namespace --replicas=1" "true"
    else
        echo -e "${YELLOW}⚠ No deployments found in test-namespace to test scaling${NC}"
    fi
else
    echo -e "${YELLOW}⚠ test-namespace not found, skipping scale tests${NC}"
fi
echo ""

echo "=== 6. Testing Scale Permissions in Protected Namespaces (Should Fail) ==="
test_command "Scale in kube-system (should fail)" "kubectl scale deployment/coredns -n kube-system --replicas=2" "false"
test_command "Scale in argocd (should fail)" "kubectl get deployment -n argocd --no-headers 2>/dev/null | head -1 | awk '{print \$1}' | xargs -I {} kubectl scale deployment/{} -n argocd --replicas=1" "false"
test_command "Scale in istio-system (should fail)" "kubectl get deployment -n istio-system --no-headers 2>/dev/null | head -1 | awk '{print \$1}' | xargs -I {} kubectl scale deployment/{} -n istio-system --replicas=1" "false"
echo ""

echo "=== 7. Testing Write Permissions (Should All Fail) ==="
test_command "Create pod (should fail)" "kubectl run test-pod --image=nginx -n default" "false"
test_command "Delete pod (should fail)" "kubectl delete pod test-pod -n default" "false"
test_command "Create deployment (should fail)" "kubectl create deployment test-deploy --image=nginx -n default" "false"
echo ""

echo "=== 8. Testing ServiceAccount Configuration ==="
echo -n "Checking ServiceAccount ... "
SA=$(kubectl get sa kubectl-runner -n task-scheduler -o jsonpath='{.metadata.name}' 2>/dev/null)
if [ "$SA" = "kubectl-runner" ]; then
    echo -e "${GREEN}✓ ServiceAccount exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ ServiceAccount not found${NC}"
    ((FAILED++))
fi

echo -n "Checking IAM role annotation ... "
ROLE_ARN=$(kubectl get sa kubectl-runner -n task-scheduler -o jsonpath='{.metadata.annotations.eks\.amazonaws\.com/role-arn}' 2>/dev/null)
if [ ! -z "$ROLE_ARN" ]; then
    echo -e "${GREEN}✓ IAM role annotation present: $ROLE_ARN${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ IAM role annotation missing${NC}"
    ((FAILED++))
fi
echo ""

echo "=== 9. Testing ClusterRole and Bindings ==="
echo -n "Checking kubectl-runner-readonly ClusterRole ... "
if kubectl get clusterrole kubectl-runner-readonly &> /dev/null; then
    echo -e "${GREEN}✓ ClusterRole exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ ClusterRole not found${NC}"
    ((FAILED++))
fi

echo -n "Checking kubectl-runner-scale ClusterRole ... "
if kubectl get clusterrole kubectl-runner-scale &> /dev/null; then
    echo -e "${GREEN}✓ ClusterRole exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ ClusterRole not found${NC}"
    ((FAILED++))
fi

echo -n "Checking ClusterRoleBinding for readonly ... "
if kubectl get clusterrolebinding kubectl-runner-readonly &> /dev/null; then
    echo -e "${GREEN}✓ ClusterRoleBinding exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ ClusterRoleBinding not found${NC}"
    ((FAILED++))
fi

echo -n "Checking ClusterRoleBinding for scale ... "
if kubectl get clusterrolebinding kubectl-runner-scale &> /dev/null; then
    echo -e "${GREEN}✓ ClusterRoleBinding exists${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ ClusterRoleBinding not found${NC}"
    ((FAILED++))
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the RBAC configuration.${NC}"
    exit 1
fi
