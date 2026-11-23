#!/usr/bin/env bash
# Deploy the Interactive AI Mystery Engine to Google Cloud Run.
#
# Prerequisites:
#   - gcloud CLI authenticated (`gcloud auth login`)
#   - Secret `GOOGLE_API_KEY` stored in Google Cloud Secret Manager
#
# Usage:
#   export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
#   export GOOGLE_CLOUD_LOCATION="us-central1"
#   ./deploy/deploy_cloud_run.sh

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT before deploying}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-mystery-engine-adk}"

echo "Deploying ${SERVICE_NAME} to Cloud Run (${PROJECT_ID} / ${REGION})..."

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="." \
  --allow-unauthenticated \
  --memory="1Gi" \
  --cpu="1" \
  --min-instances="0" \
  --max-instances="3" \
  --set-env-vars="LOG_FORMAT=json,OTEL_EXPORTER=cloud_trace,SESSION_BACKEND=sqlite,MYSTERY_MODEL=gemini-3.5-flash" \
  --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest"

echo "Deployment complete!"
