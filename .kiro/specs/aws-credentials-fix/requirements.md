# Requirements Document

## Introduction

The namespace controller pod is currently unable to access AWS DynamoDB due to missing AWS credentials configuration. This feature addresses the authentication issue by implementing IAM Roles for Service Accounts (IRSA) to provide secure, temporary AWS credentials to the controller pod without storing long-term credentials.

## Glossary

- **Controller_Pod**: The Kubernetes pod running the namespace controller application
- **ServiceAccount**: The Kubernetes ServiceAccount `scaler-sa` used by the Controller_Pod
- **IRSA**: IAM Roles for Service Accounts - AWS feature that allows Kubernetes pods to assume IAM roles
- **IAM_Role**: AWS Identity and Access Management role with DynamoDB permissions
- **DynamoDB_Table**: The `NamespaceSchedules` table that the controller needs to access
- **Trust_Relationship**: IAM policy that allows the EKS cluster's OIDC provider to assume the IAM role
- **EKS_Cluster**: The Amazon Elastic Kubernetes Service cluster hosting the controller
- **OIDC_Provider**: OpenID Connect identity provider associated with the EKS cluster

## Requirements

### Requirement 1: IAM Role Creation

**User Story:** As a platform engineer, I want to create an IAM role with appropriate DynamoDB permissions, so that the controller pod can securely access the NamespaceSchedules table.

#### Acceptance Criteria

1. THE IAM_Role SHALL be created with a descriptive name indicating its purpose for the namespace controller
2. THE IAM_Role SHALL have permissions to read, write, update, and delete items in the DynamoDB_Table
3. THE IAM_Role SHALL have permissions to describe the DynamoDB_Table structure
4. THE IAM_Role SHALL follow the principle of least privilege by only granting necessary DynamoDB permissions
5. THE IAM_Role SHALL include appropriate tags for resource management and cost tracking

### Requirement 2: IRSA Trust Relationship Configuration

**User Story:** As a platform engineer, I want to configure the IAM role trust relationship for IRSA, so that the Kubernetes ServiceAccount can assume the role securely.

#### Acceptance Criteria

1. THE Trust_Relationship SHALL allow the EKS_Cluster's OIDC_Provider to assume the IAM_Role
2. THE Trust_Relationship SHALL restrict role assumption to the specific ServiceAccount name `scaler-sa`
3. THE Trust_Relationship SHALL restrict role assumption to the specific namespace `encendido-eks`
4. WHEN the trust relationship is configured, THE OIDC_Provider SHALL be able to validate the ServiceAccount token
5. THE Trust_Relationship SHALL use the `sts:AssumeRoleWithWebIdentity` action

### Requirement 3: ServiceAccount Annotation

**User Story:** As a platform engineer, I want to annotate the ServiceAccount with the IAM role ARN, so that the controller pod can discover and assume the correct IAM role.

#### Acceptance Criteria

1. THE ServiceAccount SHALL be annotated with the key `eks.amazonaws.com/role-arn`
2. THE ServiceAccount annotation SHALL contain the full ARN of the created IAM_Role
3. WHEN the ServiceAccount is annotated, THE Controller_Pod SHALL automatically discover the role ARN
4. THE ServiceAccount SHALL exist in the correct namespace `encendido-eks`
5. THE ServiceAccount SHALL maintain any existing annotations and labels

### Requirement 4: AWS Credentials Resolution

**User Story:** As a controller application, I want to automatically obtain AWS credentials through IRSA, so that I can authenticate to AWS services without manual credential management.

#### Acceptance Criteria

1. WHEN the Controller_Pod starts, THE AWS SDK SHALL automatically discover and use the IRSA credentials
2. THE Controller_Pod SHALL obtain temporary AWS credentials through the ServiceAccount token
3. THE AWS credentials SHALL be automatically refreshed before expiration
4. WHEN accessing DynamoDB_Table, THE Controller_Pod SHALL use the assumed role credentials
5. THE Controller_Pod SHALL NOT require any hardcoded AWS credentials or access keys

### Requirement 5: DynamoDB Access Validation

**User Story:** As a controller application, I want to successfully access the DynamoDB table, so that I can perform namespace scheduling operations.

#### Acceptance Criteria

1. WHEN the Controller_Pod attempts to read from DynamoDB_Table, THE operation SHALL succeed without authentication errors
2. WHEN the Controller_Pod attempts to write to DynamoDB_Table, THE operation SHALL succeed without authentication errors
3. WHEN the Controller_Pod attempts to update items in DynamoDB_Table, THE operation SHALL succeed without authentication errors
4. WHEN the Controller_Pod attempts to delete items from DynamoDB_Table, THE operation SHALL succeed without authentication errors
5. THE Controller_Pod SHALL be able to describe the DynamoDB_Table structure for operational purposes

### Requirement 6: Error Handling and Logging

**User Story:** As a platform engineer, I want clear error messages and logging for credential issues, so that I can troubleshoot authentication problems effectively.

#### Acceptance Criteria

1. WHEN IRSA credential assumption fails, THE Controller_Pod SHALL log descriptive error messages
2. WHEN DynamoDB access is denied, THE Controller_Pod SHALL log the specific permission that was denied
3. WHEN the ServiceAccount annotation is missing or invalid, THE Controller_Pod SHALL log a clear error message
4. THE Controller_Pod SHALL log successful credential assumption for debugging purposes
5. THE Controller_Pod SHALL NOT log sensitive credential information in plain text

### Requirement 7: Infrastructure as Code

**User Story:** As a platform engineer, I want the AWS infrastructure changes to be defined as code, so that the configuration is reproducible and version-controlled.

#### Acceptance Criteria

1. THE IAM_Role creation SHALL be defined in infrastructure as code (Terraform, CloudFormation, or similar)
2. THE Trust_Relationship configuration SHALL be defined in infrastructure as code
3. THE ServiceAccount annotation SHALL be defined in Kubernetes manifests
4. WHEN infrastructure code is applied, THE complete IRSA setup SHALL be configured correctly
5. THE infrastructure code SHALL include appropriate variable definitions for reusability across environments