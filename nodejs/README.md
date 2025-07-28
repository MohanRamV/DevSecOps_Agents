# CI/CD Pipeline

This repository contains a comprehensive CI/CD pipeline for a Node.js application using GitHub Actions. The pipeline automates testing, linting, building, Docker image creation, security scanning, and Kubernetes deployment updates.

## Pipeline Overview

The pipeline is triggered on:
- Push to the `main` branch (when changes are made to the `nodejs/` directory)
- Pull requests to the `main` branch

## Pipeline Stages

### 1. Unit Testing
- **Job Name**: `test`
- **Purpose**: Runs unit tests for the Node.js application
- **Steps**:
  - Checks out the repository code
  - Sets up Node.js version 20 with npm caching
  - Installs dependencies using `npm ci`
  - Executes tests with `npm test`
  - Includes fallback message if no tests are found

### 2. Static Code Analysis
- **Job Name**: `lint`
- **Purpose**: Performs code quality checks using ESLint
- **Steps**:
  - Checks out the repository code
  - Sets up Node.js environment
  - Installs dependencies
  - Runs ESLint for code analysis

### 3. Build
- **Job Name**: `build`
- **Purpose**: Builds the Node.js application
- **Dependencies**: Requires both `test` and `lint` jobs to pass
- **Steps**:
  - Builds the project using `npm run build`
  - Uploads build artifacts to GitHub Actions for use in subsequent jobs

### 4. Docker Build and Push
- **Job Name**: `docker`
- **Purpose**: Creates and pushes Docker images to GitHub Container Registry
- **Dependencies**: Requires `build` job to complete
- **Key Features**:
  - Downloads build artifacts from the previous stage
  - Sets up Docker Buildx for advanced building capabilities
  - Authenticates with GitHub Container Registry (GHCR)
  - Generates metadata and tags for the Docker image
  - Performs security scanning using Trivy
  - Pushes the final image to the registry

**Image Tags Generated**:
- `sha-{full-commit-hash}` - Full SHA tag
- `{branch-name}` - Branch-based tag
- `latest` - Latest tag

**Security Scanning**:
- Uses Aqua Security Trivy to scan for vulnerabilities
- Scans for OS and library vulnerabilities
- Fails the build on CRITICAL or HIGH severity issues
- Ignores unfixed vulnerabilities

### 5. Kubernetes Deployment Update
- **Job Name**: `update-k8s`
- **Purpose**: Automatically updates Kubernetes deployment files with new image tags
- **Trigger Conditions**: 
  - Only runs on pushes to the `main` branch
  - Skips on pull requests
- **Steps**:
  - Updates the `nodejs/kubernetes/deployment.yaml` file with the new image tag
  - Commits and pushes the changes back to the repository
  - Uses `[skip ci]` in commit message to prevent triggering another pipeline run

## Prerequisites

### Required Secrets
The pipeline requires the following GitHub secrets to be configured:

- `TOKEN`: GitHub Personal Access Token with appropriate permissions for:
  - Container registry access
  - Repository write access for updating Kubernetes files

### Repository Structure
```
├── nodejs/
│   ├── package.json
│   ├── package-lock.json
│   ├── Dockerfile
│   ├── dist/                 # Build output directory
│   └── kubernetes/
│       └── deployment.yaml   # Kubernetes deployment file
└── .github/
    └── workflows/
        └── ci-cd.yml         # This pipeline file
```

### Required npm Scripts
Your `package.json` should include these scripts:
```json
{
  "scripts": {
    "test": "your-test-command",
    "lint": "eslint .",
    "build": "your-build-command"
  }
}
```

## Container Registry

The pipeline uses GitHub Container Registry (GHCR) to store Docker images:
- **Registry**: `ghcr.io`
- **Image naming**: `ghcr.io/{username}/{repository}:{tag}`
- **Authentication**: Uses GitHub token authentication

## Deployment Strategy

The pipeline implements a GitOps approach:
1. Code changes trigger the pipeline
2. New Docker images are built and pushed
3. Kubernetes deployment files are automatically updated
4. Changes are committed back to the repository
5. External deployment tools (like ArgoCD or Flux) can watch for these changes and deploy to clusters

## Security Features

- **Vulnerability Scanning**: Trivy scans all Docker images for security vulnerabilities
- **Dependency Caching**: Uses npm cache to speed up builds and reduce external dependencies
- **Least Privilege**: Uses GitHub's built-in authentication tokens
- **Fail-Fast**: Pipeline stops on test failures, linting errors, or security issues

## Monitoring and Troubleshooting

### Common Issues
1. **Build Failures**: Check the test and lint jobs for specific error messages
2. **Docker Push Issues**: Verify the `TOKEN` secret has container registry permissions
3. **Kubernetes Update Failures**: Ensure the token has write access to the repository

### Logs and Artifacts
- Build artifacts are stored in GitHub Actions for 90 days (default)
- All job logs are available in the GitHub Actions interface
- Docker images are tagged with commit SHAs for traceability

## Customization

To adapt this pipeline for your project:

1. Update the `working-directory` if your Node.js app is in a different location
2. Modify the `paths` filter to match your project structure
3. Adjust Node.js version in the setup steps if needed
4. Customize Docker build context and file paths
5. Update Kubernetes file paths to match your deployment structure

## Performance Optimizations

- **Parallel Execution**: Test and lint jobs run in parallel
- **Dependency Caching**: npm dependencies are cached between runs
- **Conditional Execution**: Kubernetes updates only run on main branch pushes
- **Artifact Reuse**: Build artifacts are shared between jobs to avoid rebuilding