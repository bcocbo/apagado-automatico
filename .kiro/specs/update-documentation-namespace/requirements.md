# Requirements: Update Documentation for Namespace Change

## Overview
The ArgoCD application configuration has been updated to change the namespace from `namespace-scheduler` to `task-scheduler`, and the repository URL has been updated. The documentation needs to be updated to reflect these changes consistently throughout all documentation files.

## User Stories

### 1. As a developer, I need the documentation to accurately reflect the current namespace configuration
**Acceptance Criteria:**
- 1.1 All references to `namespace-scheduler` namespace are updated to `task-scheduler`
- 1.2 All references to the old repository URL are updated to the new URL
- 1.3 The ArgoCD application name is correctly documented as `task-scheduler`
- 1.4 All kubectl commands use the correct namespace `task-scheduler`
- 1.5 All URL examples use the correct namespace in paths

### 2. As a developer, I need consistent naming across all documentation files
**Acceptance Criteria:**
- 2.1 README-TASK-SCHEDULER.md is updated with correct namespace references
- 2.2 All code examples and commands reflect the new namespace
- 2.3 Architecture diagrams or descriptions reference the correct namespace
- 2.4 Troubleshooting sections use the correct namespace in diagnostic commands

### 3. As a developer, I need the ArgoCD configuration documentation to be accurate
**Acceptance Criteria:**
- 3.1 The ArgoCD application deployment instructions reference the correct file
- 3.2 The repository URL is correctly documented as `https://github.com/bcocbo/apagado-automatico.git`
- 3.3 The namespace configuration in syncPolicy is documented correctly

## Constraints
- Must maintain backward compatibility notes if the old namespace was previously documented
- Should not change the actual functionality, only documentation
- Must ensure all code snippets are executable with the new namespace

## Out of Scope
- Updating actual Kubernetes manifests (already done)
- Changing the ArgoCD configuration file (already done)
- Modifying application code
