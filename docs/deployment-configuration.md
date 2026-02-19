# Deployment Configuration

## Image Management Strategy

The Namespace Scheduler uses Kustomize for managing different deployment environments. The image configuration follows this pattern:

### Base Configuration
The base deployment manifests (`manifests/base/task-scheduler-deployment.yaml`) use generic image names:
- `task-scheduler-frontend:latest`
- `task-scheduler-backend:latest`

### Production Overlay
The production overlay (`manifests/overlays/production/kustomization.yaml`) replaces these generic names with actual ECR registry URLs:
- `226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-frontend:latest`
- `226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-backend:latest`

This approach allows:
1. **Environment flexibility**: Different overlays can use different registries
2. **Clean base manifests**: Base configurations remain registry-agnostic
3. **Automated updates**: CI/CD can update image tags in overlays without touching base files

## Kustomize Image Replacement

The production overlay uses Kustomize's `images` field to replace image references:

```yaml
images:
- name: task-scheduler-frontend
  newName: 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-frontend
  newTag: latest
- name: task-scheduler-backend
  newName: 226633502530.dkr.ecr.us-east-1.amazonaws.com/task-scheduler-backend
  newTag: latest
```

## CI/CD Integration

GitHub Actions actualiza automáticamente los image tags en el mismo repositorio:

### Proceso Automatizado
1. **Build**: GitHub Actions construye y pushea imágenes a ECR con tag basado en commit SHA
2. **Update**: El workflow actualiza `manifests/overlays/production/kustomization.yaml` con el nuevo tag
3. **Commit**: Los cambios se commitean automáticamente con mensaje `[skip ci]`
4. **Deploy**: ArgoCD detecta los cambios y sincroniza el cluster

### Ventajas de esta Estrategia
- **Simplicidad**: Todo en un solo repositorio
- **Trazabilidad**: Cada commit tiene su imagen correspondiente
- **Atomicidad**: Código e infraestructura se actualizan juntos
- **GitOps**: ArgoCD maneja el despliegue basado en Git

## Deployment Process

1. **Build**: GitHub Actions builds and pushes images to ECR with commit SHA as tag
2. **Update**: CI/CD updates image tags in `manifests/overlays/production/kustomization.yaml` using `sed`
3. **Commit**: Changes are automatically committed with `[skip ci]` to avoid infinite loops
4. **Deploy**: ArgoCD syncs the production overlay to the cluster
5. **Result**: Kustomize applies the overlay, replacing generic names with ECR URLs and specific tags

## Infrastructure Components

### DynamoDB Tables
The project uses DynamoDB for persistent storage of logs and configuration:
- **CloudFormation template**: `infrastructure/dynamodb-tables.yaml`
- **Main table**: `task-scheduler-logs-{environment}`
- **Deployment**: Deploy infrastructure before application using CloudFormation

```bash
# Deploy DynamoDB infrastructure
aws cloudformation deploy \
  --template-file infrastructure/dynamodb-tables.yaml \
  --stack-name namespace-scheduler-dynamodb \
  --parameter-overrides Environment=production
```

### Kubernetes RBAC
The kubectl-runner service requires specific RBAC permissions to manage namespaces and resources:
- **Configuration**: `manifests/base/kubectl-runner-rbac.yaml`
- **Documentation**: See [kubernetes-rbac-configuration.md](kubernetes-rbac-configuration.md) for detailed RBAC setup
- **Security**: Current configuration uses broad permissions and requires review (Task 1.4)

### Rollback System
The backend implements automatic rollback for scaling operations to ensure atomicity:
- **Documentation**: See [rollback-implementation.md](rollback-implementation.md) for detailed rollback behavior
- **Features**:
  - Automatic rollback on partial failures during scaling operations
  - Tracks all successful operations for potential reversion
  - Detailed logging and audit trail of rollback operations
  - Configurable rollback behavior (can be disabled for testing)
- **Guarantees**: Either all resources scale successfully, or all are reverted to original state

### Initial Data Population
A Kubernetes Job is provided to populate the cost-center-permissions table with initial data:
- **Job manifest**: `manifests/base/populate-permissions-job.yaml`
- **Execution**: Run `kubectl apply -f manifests/base/populate-permissions-job.yaml`
- **Features**:
  - Uses `python:3.11-slim` image with boto3
  - Runs with `kubectl-runner` ServiceAccount (has IAM permissions for DynamoDB)
  - Auto-cleanup after 5 minutes (ttlSecondsAfterFinished: 300)
  - Idempotent: won't overwrite existing records
  - Populates 6 default cost centers (5 authorized, 1 disabled)
- **Documentation**: See [cost-center-permissions-setup.md](cost-center-permissions-setup.md) for details

### IAM Integration
EKS integration with AWS services requires proper IAM configuration:
- **Service Account**: Annotated with IAM role ARN for AWS access
- **Authentication**: Automatic detection of execution environment
  - **In EKS Pod**: Uses service account token authentication (IRSA)
  - **Local/CI-CD**: Uses AWS kubeconfig authentication
- **Documentation**: See [eks-iam-configuration.md](eks-iam-configuration.md) for IAM setup

### Kubernetes Authentication

The kubectl-runner backend implements automatic authentication detection:

#### Service Account Token Authentication (Production)
When running in an EKS pod, the application automatically detects the presence of the service account token at `/var/run/secrets/kubernetes.io/serviceaccount/token` and uses it for authentication. This provides:
- **Automatic Authentication**: No manual kubeconfig setup required
- **IRSA Integration**: Seamless integration with IAM Roles for Service Accounts
- **Security**: Uses Kubernetes-native authentication mechanisms

#### AWS kubeconfig Authentication (Development/CI-CD)
When running outside of a Kubernetes pod (local development or CI/CD), the application:
- Detects the absence of service account token
- Automatically configures kubeconfig using `aws eks update-kubeconfig`
- Uses AWS credentials for cluster access
- Requires proper AWS IAM permissions

#### Environment Detection Logic
```python
# Automatic detection of execution environment
in_k8s_pod = os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token')

if not in_k8s_pod and not os.path.exists('/root/.kube/config'):
    # Configure kubeconfig for local/CI-CD environments
    subprocess.run(['aws', 'eks', 'update-kubeconfig', '--region', region, '--name', cluster_name])
```

This dual authentication approach ensures the same codebase works seamlessly across all deployment environments without manual configuration.

### Resource Configuration

The production overlay also configures resource limits and requests for both frontend and backend containers:

#### Frontend Resources
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

#### Backend Resources
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "200m"
  limits:
    memory: "1Gi"
    cpu: "500m"
```

These resource configurations ensure:
- **Frontend**: Lightweight resource allocation suitable for serving static content via nginx
- **Backend**: Adequate resources for Python Flask application with kubectl operations and DynamoDB access
- **Resource Requests**: Guaranteed minimum resources for scheduling
- **Resource Limits**: Maximum resources to prevent resource exhaustion

### Environment Configuration

### Production Environment Variables
The production overlay configures the backend with the following environment variables:

```yaml
env:
- name: EKS_CLUSTER_NAME
  value: "eks-cloud"
- name: AWS_REGION
  value: "us-east-1"
- name: DYNAMODB_TABLE_NAME
  value: "task-scheduler-logs-production"
- name: PERMISSIONS_TABLE_NAME
  value: "cost-center-permissions-production"
- name: LOG_LEVEL
  value: "WARNING"
- name: BUSINESS_HOURS_TIMEZONE
  value: "America/Bogota"
- name: BUSINESS_START_HOUR
  value: "8"
- name: BUSINESS_END_HOUR
  value: "18"
- name: BUSINESS_HOLIDAYS
  value: ""
- name: BUSINESS_HOLIDAYS_COUNTRY
  value: "CO"
- name: BUSINESS_HOLIDAYS_SUBDIVISION
  value: ""
```

These variables are set in `manifests/overlays/production/task-scheduler-patch.yaml` and provide:
- **EKS_CLUSTER_NAME**: Identifies the target cluster for operations
- **AWS_REGION**: AWS region for DynamoDB and other AWS service calls
- **DYNAMODB_TABLE_NAME**: Production table for task execution logs (includes "-production" suffix)
- **PERMISSIONS_TABLE_NAME**: Production table for cost center permissions (includes "-production" suffix)
- **LOG_LEVEL**: Log level for production environment (set to "WARNING" to reduce log volume)
- **BUSINESS_HOURS_TIMEZONE**: Timezone for business hours calculation (set to "America/Bogota" for Colombia)
- **BUSINESS_START_HOUR**: Business day start hour in 24-hour format (8 AM)
- **BUSINESS_END_HOUR**: Business day end hour in 24-hour format (6 PM)
- **BUSINESS_HOLIDAYS**: Comma-separated manual holiday dates (empty - using automatic detection)
- **BUSINESS_HOLIDAYS_COUNTRY**: Country code for automatic holiday detection ("CO" for Colombia)
- **BUSINESS_HOLIDAYS_SUBDIVISION**: State/province for regional holidays (empty for country-wide holidays)

**Note**: The production environment uses table names with the "-production" suffix to separate production data from development/testing environments. This naming convention is consistent across all deployment scripts and infrastructure components. The production environment is configured for Colombia timezone (America/Bogota) with business hours from 8 AM to 6 PM and automatic Colombian holiday detection.

### Structured Logging

The backend implements structured logging with support for JSON and text formats:

- **JSON Format** (default): Machine-readable structured logs for integration with CloudWatch, ELK, Splunk
- **Text Format**: Human-readable logs for local development
- **Request Tracing**: Automatic request ID generation and correlation across log entries
- **Log Rotation**: Automatic rotation at 10 MB with 5 backup files retained
- **Contextual Fields**: Automatic capture of user, namespace, cost center, cluster, and operation metadata

For detailed configuration and usage, see [Structured Logging Configuration](structured-logging-configuration.md).

### Permissions Cache

The backend implements an in-memory cache for cost center permissions to reduce DynamoDB read operations and improve performance:

- **Cache TTL**: Configurable via `PERMISSIONS_CACHE_TTL` (default: 300 seconds / 5 minutes)
- **Cache Control**: Can be enabled/disabled via `PERMISSIONS_CACHE_ENABLED` environment variable
- **Cache Invalidation**: Automatically invalidated when permissions are updated via API
- **Negative Caching**: Failed lookups are also cached to prevent repeated queries for non-existent cost centers
- **Cache Stats**: Available via `/api/cache/stats` endpoint for monitoring

Benefits:
- Reduces DynamoDB read costs
- Improves response time for permission checks
- Reduces load on DynamoDB during high-traffic periods

## Configuration Files

- **Infrastructure**: `infrastructure/dynamodb-tables.yaml`
- **Base deployment**: `manifests/base/task-scheduler-deployment.yaml`
- **Base kustomization**: `manifests/base/kustomization.yaml`
- **RBAC configuration**: `manifests/base/kubectl-runner-rbac.yaml`
- **Data population job**: `manifests/base/populate-permissions-job.yaml`
- **Production overlay**: `manifests/overlays/production/kustomization.yaml`
- **Production patches**: `manifests/overlays/production/task-scheduler-patch.yaml`
- **ArgoCD app**: `argocd/namespace-scheduler-app.yaml`

## Related Documentation

- [Local Development Setup](local-development-setup.md) - Running the backend locally for development
- [Structured Logging Configuration](structured-logging-configuration.md) - Logging setup and configuration
- [Kubernetes RBAC Configuration](kubernetes-rbac-configuration.md) - RBAC permissions setup
- [EKS IAM Configuration](eks-iam-configuration.md) - IAM roles and policies
- [Cost Center Permissions Setup](cost-center-permissions-setup.md) - Permissions table setup
- [Rollback Implementation](rollback-implementation.md) - Automatic rollback behavior
- [DynamoDB Table Design](dynamodb-table-design.md) - Database schema and indexes