#!/usr/bin/env bash
# Phase 1 manual deploy of TuViMCP FastAPI to Cloud Run (asia-southeast1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROJECT="${GCP_PROJECT:-tuvi-mcp-prod}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE="${CLOUD_RUN_SERVICE:-tuvi-mcp}"

if [[ -z "${SUPABASE_URL:-}" ]]; then
  if [[ -f "$ROOT/.env" ]]; then
    # shellcheck disable=SC1091
    set -a && source "$ROOT/.env" && set +a
  fi
fi

if [[ -z "${SUPABASE_URL:-}" ]]; then
  echo "SUPABASE_URL is required (export it or set in .env)" >&2
  exit 1
fi

gcloud config set project "$PROJECT"
gcloud config set run/region "$REGION"

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --timeout 120 \
  --concurrency 40 \
  --allow-unauthenticated \
  --set-env-vars "TUVI_MCP_ENV=production,SUPABASE_URL=${SUPABASE_URL}"

gcloud run services describe "$SERVICE" \
  --region "$REGION" \
  --format='value(status.url)'
