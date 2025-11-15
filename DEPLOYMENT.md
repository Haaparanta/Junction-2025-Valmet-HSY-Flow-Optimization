# Google Cloud Deployment Guide

This guide explains how to deploy the backend and frontend to Google Cloud Platform.

## Prerequisites

1. Google Cloud Project with billing enabled
2. Cloud Build API enabled
3. Container Registry API or Artifact Registry API enabled
4. `gcloud` CLI installed and authenticated

## Setup

### Option 1: Using Artifact Registry (Recommended)

1. Create an Artifact Registry repository:
```bash
gcloud artifacts repositories create junction-valmet \
  --repository-format=docker \
  --location=europe-north1 \
  --description="Docker repository for Junction Valmet project"
```

2. Use `cloudbuild.yaml` (default configuration)

3. Submit the build:
```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=europe-north1,_REPOSITORY=junction-valmet
```

### Option 2: Using Container Registry (Legacy)

1. Use `cloudbuild-gcr.yaml`:
```bash
gcloud builds submit --config=cloudbuild-gcr.yaml
```

## Cloud Build Configuration

The `cloudbuild.yaml` file:
- Builds the Docker image from the `backend/` directory
- Uses the Dockerfile located at `backend/Dockerfile`
- Tags the image with both SHORT_SHA and `latest`
- Pushes to Artifact Registry

## Customization

### Change Region
Edit the `_REGION` substitution variable in `cloudbuild.yaml` or pass it via command line:
```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1
```

### Change Repository Name
Edit the `_REPOSITORY` substitution variable or pass it via command line:
```bash
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_REPOSITORY=my-repo-name
```

## Deploying to Cloud Run

To deploy the backend to Cloud Run, uncomment the deployment step in `cloudbuild.yaml`:

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  entrypoint: gcloud
  args:
    - 'run'
    - 'deploy'
    - 'backend'
    - '--image'
    - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/backend:${SHORT_SHA}'
    - '--region'
    - '${_REGION}'
    - '--platform'
    - 'managed'
```

Or deploy manually after the build:
```bash
gcloud run deploy backend \
  --image gcr.io/PROJECT_ID/backend:latest \
  --region europe-north1 \
  --platform managed
```

## Frontend Deployment

If you have a frontend application, add similar build steps to `cloudbuild.yaml`:

```yaml
# Build frontend Docker image
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '-t'
    - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/${_REPOSITORY}/frontend:${SHORT_SHA}'
    - '-f'
    - 'frontend/Dockerfile'
    - 'frontend'
  id: 'build-frontend'
```

## Troubleshooting

### Error: "unable to evaluate symlinks in Dockerfile path"
- **Solution**: Ensure you're using `cloudbuild.yaml` which specifies the correct Dockerfile path (`-f backend/Dockerfile`)

### Error: "Permission denied"
- **Solution**: Ensure Cloud Build has the necessary permissions:
```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/run.admin
```

### Error: "Repository not found"
- **Solution**: Create the Artifact Registry repository first (see Option 1 above)

