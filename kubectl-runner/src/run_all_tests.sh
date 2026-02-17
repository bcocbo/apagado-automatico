#!/bin/bash
# Run all validation tests for the kubectl-runner API

echo "Running all validation tests..."
echo "================================"
echo ""

# Check if the API is running
echo "Checking if API is available at http://localhost:8080..."
if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "ERROR: API is not running at http://localhost:8080"
    echo "Please start the API server before running tests"
    exit 1
fi

echo "✓ API is running"
echo ""

# Run cost center validation tests
echo "Running cost center validation tests..."
python3 test_cost_center_validation.py
if [ $? -ne 0 ]; then
    echo "✗ Cost center validation tests failed"
    exit 1
fi
echo ""

# Run namespace validation tests
echo "Running namespace validation tests..."
python3 test_namespace_validation.py
if [ $? -ne 0 ]; then
    echo "✗ Namespace validation tests failed"
    exit 1
fi
echo ""

# Run task creation validation tests
echo "Running task creation validation tests..."
python3 test_task_creation_validation.py
if [ $? -ne 0 ]; then
    echo "✗ Task creation validation tests failed"
    exit 1
fi
echo ""

# Run permissions cache tests
echo "Running permissions cache tests..."
python3 test_permissions_cache.py
if [ $? -ne 0 ]; then
    echo "✗ Permissions cache tests failed"
    exit 1
fi
echo ""

# Run user tracking tests
echo "Running user tracking tests..."
python3 test_user_tracking.py
if [ $? -ne 0 ]; then
    echo "✗ User tracking tests failed"
    exit 1
fi
echo ""

# Run cluster name capture tests
echo "Running cluster name capture tests..."
python3 test_cluster_name_capture.py
if [ $? -ne 0 ]; then
    echo "✗ Cluster name capture tests failed"
    exit 1
fi
echo ""

# Run audit endpoints tests
echo "Running audit endpoints tests..."
python3 test_audit_endpoints.py
if [ $? -ne 0 ]; then
    echo "✗ Audit endpoints tests failed"
    exit 1
fi
echo ""

# Run active namespace counting tests
echo "Running active namespace counting tests..."
python3 test_active_namespace_counting.py
if [ $? -ne 0 ]; then
    echo "✗ Active namespace counting tests failed"
    exit 1
fi
echo ""

# Run business hours detection tests
echo "Running business hours detection tests..."
python3 test_business_hours_detection.py
if [ $? -ne 0 ]; then
    echo "✗ Business hours detection tests failed"
    exit 1
fi
echo ""

echo "================================"
echo "All tests passed successfully! ✓"
exit 0
