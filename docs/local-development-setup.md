# Local Development Setup

## Overview

The Namespace Scheduler backend can be run locally for development and testing purposes. Three scripts are provided:

- `kubectl-runner/src/start-local.sh` - Bash script for basic local setup
- `kubectl-runner/src/run-local.py` - Python script with path patching for local development
- `kubectl-runner/src/run-production.py` - Python script for connecting to production EKS cluster

## Quick Start

### Using Python Runner for Local Development (Recommended)

The Python runner automatically patches hardcoded container paths to work in local development:

```bash
cd kubectl-runner/src
python3 run-local.py
```

### Using Production Runner

To connect to the production EKS cluster from your local machine:

```bash
cd kubectl-runner/src
python3 run-production.py
```

**Prerequisites for production runner:**
- AWS credentials configured with access to production resources
- kubectl configured with access to the EKS cluster
- Proper IAM permissions for DynamoDB and EKS

**Note**: The application automatically detects if it's running in a Kubernetes pod (by checking for service account token) and uses the appropriate authentication method:
- **In EKS Pod**: Uses service account token authentication (IRSA)
- **Local Development**: Uses AWS kubeconfig authentication

### Using Bash Script

The bash script sets up environment variables but doesn't patch hardcoded paths:

```bash
cd kubectl-runner/src
./start-local.sh
```

## Python Runner Features

### Local Development Runner (`run-local.py`)

The `run-local.py` script provides:

1. **Automatic Directory Creation**: Creates `./logs` and `./config` directories
2. **Path Patching**: Patches hardcoded `/app` paths to local relative paths
3. **Environment Configuration**: Sets up all required environment variables for local testing
4. **Development Mode**: Enables Flask debug mode for hot reloading

### Production Runner (`run-production.py`)

The `run-production.py` script provides:

1. **Automatic Directory Creation**: Creates `./logs` and `./config` directories
2. **Path Patching**: Patches hardcoded `/app` paths to local relative paths
3. **Production Environment Configuration**: Connects to production DynamoDB tables and EKS cluster
4. **Production Mode**: Runs Flask in production mode (debug disabled)

**Use cases for production runner:**
- Testing changes against production data without deploying
- Debugging production issues locally
- Running administrative tasks on production resources
- Validating configurations before deployment

### Path Patching

Both Python runners patch the following hardcoded paths in `app.py`:
- `/app/logs` → `./logs`
- `/app/config` → `./config`

This allows the application to run without Docker while maintaining compatibility with the containerized deployment.

## Local Environment Variables

### Local Development (`run-local.py`)

The local development script configures the following environment variables:

| Variable | Local Value | Description |
|----------|-------------|-------------|
| `LOG_FILE` | `./logs/app.log` | Local log file path |
| `FLASK_ENV` | `development` | Flask environment mode |
| `FLASK_DEBUG` | `1` | Enable Flask debug mode |
| `EKS_CLUSTER_NAME` | `local-cluster` | Cluster identifier for local testing |
| `AWS_REGION` | `us-east-1` | AWS region for DynamoDB access |
| `DYNAMODB_TABLE_NAME` | `task-scheduler-logs-local` | Local DynamoDB table name |
| `PERMISSIONS_TABLE_NAME` | `cost-center-permissions-local` | Local permissions table name |

### Production Connection (`run-production.py`)

The production runner script configures the following environment variables:

| Variable | Production Value | Description |
|----------|-----------------|-------------|
| `LOG_FILE` | `./logs/app.log` | Local log file path |
| `FLASK_ENV` | `production` | Flask environment mode |
| `EKS_CLUSTER_NAME` | `eks-cloud` | Production EKS cluster name |
| `AWS_REGION` | `us-east-1` | AWS region for DynamoDB access |
| `DYNAMODB_TABLE_NAME` | `task-scheduler-logs-production` | Production DynamoDB table name |
| `PERMISSIONS_TABLE_NAME` | `cost-center-permissions-production` | Production permissions table name |

## Prerequisites

### Required Software
- Python 3.11 or higher
- pip (Python package manager)
- AWS CLI configured with credentials
- kubectl (if testing Kubernetes operations)

### Python Dependencies

Install required packages:

```bash
cd kubectl-runner
pip install -r requirements.txt
```

Required packages include:
- Flask
- flask-cors
- boto3
- croniter
- PyYAML

### AWS Configuration

The backend requires AWS credentials to access DynamoDB. Configure using:

```bash
aws configure
```

Or set environment variables:
```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-east-1"
```

### DynamoDB Tables

Create local DynamoDB tables for testing:

```bash
# Create main logs table
aws dynamodb create-table \
  --table-name task-scheduler-logs-local \
  --attribute-definitions \
    AttributeName=namespace_name,AttributeType=S \
    AttributeName=timestamp_start,AttributeType=N \
    AttributeName=cost_center,AttributeType=S \
    AttributeName=requested_by,AttributeType=S \
    AttributeName=cluster_name,AttributeType=S \
  --key-schema \
    AttributeName=namespace_name,KeyType=HASH \
    AttributeName=timestamp_start,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "cost-center-index",
        "KeySchema": [
          {"AttributeName": "cost_center", "KeyType": "HASH"},
          {"AttributeName": "timestamp_start", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "requested-by-timestamp-index",
        "KeySchema": [
          {"AttributeName": "requested_by", "KeyType": "HASH"},
          {"AttributeName": "timestamp_start", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      },
      {
        "IndexName": "cluster-timestamp-index",
        "KeySchema": [
          {"AttributeName": "cluster_name", "KeyType": "HASH"},
          {"AttributeName": "timestamp_start", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST

# Create permissions table
aws dynamodb create-table \
  --table-name cost-center-permissions-local \
  --attribute-definitions \
    AttributeName=cost_center,AttributeType=S \
  --key-schema \
    AttributeName=cost_center,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Alternatively, use DynamoDB Local for offline development:

```bash
# Run DynamoDB Local with Docker
docker run -p 8000:8000 amazon/dynamodb-local

# Configure endpoint in run-local.py
export AWS_DYNAMODB_ENDPOINT="http://localhost:8000"
```

## Testing Local Setup

### Health Check

Once the server is running, verify it's working:

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-17T10:30:00Z"
}
```

### API Endpoints

Test basic API functionality:

```bash
# List namespaces
curl http://localhost:5000/api/namespaces

# Get cache stats
curl http://localhost:5000/api/cache/stats

# Validate cost center
curl -X POST http://localhost:5000/api/validate-cost-center \
  -H "Content-Type: application/json" \
  -d '{"cost_center": "CC001"}'
```

## Development Workflow

### Hot Reloading

Flask debug mode enables automatic reloading when code changes:

1. Start the server with `python3 run-local.py`
2. Edit Python files in `kubectl-runner/src/`
3. Flask automatically detects changes and reloads
4. Test changes immediately without restarting

### Logging

Logs are written to `./logs/app.log` with rotation:
- Maximum file size: 10 MB
- Backup files: 5
- Format: JSON (structured logging)

View logs in real-time:
```bash
tail -f ./logs/app.log | jq .
```

### Configuration Persistence

Task configurations are saved to `./config/tasks.json`:
- Auto-saved every 5 minutes (configurable)
- Loaded on startup
- Atomic writes with backup

## Differences from Production

| Aspect | Local Development | Production Runner | Production Deployment |
|--------|------------------|-------------------|----------------------|
| Paths | `./logs`, `./config` | `./logs`, `./config` | `/app/logs`, `/app/config` |
| Tables | `*-local` suffix | `*-production` suffix | `*-production` suffix |
| Cluster | `local-cluster` | `eks-cloud` | `eks-cloud` |
| Kubernetes | Optional (mocked) | Required | Required |
| Log Format | JSON (can change to text) | JSON | JSON |
| Debug Mode | Enabled | Disabled | Disabled |
| Running Location | Local machine | Local machine | EKS Pod |

## Troubleshooting

### Port Already in Use

If port 5000 is already in use:

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or change the port in run-local.py or run-production.py
export FLASK_RUN_PORT=5001
```

### AWS Credentials Error

If you see "Unable to locate credentials":

```bash
# Verify AWS configuration
aws sts get-caller-identity

# Check environment variables
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
```

### DynamoDB Connection Error

If DynamoDB connection fails:

1. Verify tables exist: `aws dynamodb list-tables`
2. Check AWS region matches: `echo $AWS_REGION`
3. Verify IAM permissions for DynamoDB access

### Production Runner Connection Issues

If the production runner fails to connect:

1. **Verify kubectl access**: `kubectl get nodes` should show EKS cluster nodes
2. **Check AWS credentials**: Ensure you have production access
3. **Verify IAM permissions**: Your IAM user/role needs DynamoDB and EKS permissions
4. **Check table names**: Ensure production tables exist with `-production` suffix

### Import Errors

If Python modules are missing:

```bash
# Reinstall dependencies
cd kubectl-runner
pip install -r requirements.txt --upgrade
```

## Related Documentation

- [Deployment Configuration](deployment-configuration.md) - Production deployment setup
- [Structured Logging Configuration](structured-logging-configuration.md) - Logging configuration
- [DynamoDB Table Design](dynamodb-table-design.md) - Database schema
- [Cost Center Permissions Setup](cost-center-permissions-setup.md) - Permissions configuration
