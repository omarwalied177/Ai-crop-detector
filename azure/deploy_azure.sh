#!/usr/bin/env bash
# Build the API image in Azure Container Registry and deploy it to Azure Container Apps.
# Prereqs: az CLI logged in, and BUNDLE_URL set to a read SAS URL of the model bundle zip.
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-ai-crop-doctor}"  # already exists in francecentral
# EUI student subscriptions only allow polandcentral, francecentral, austriaeast,
# denmarkeast and italynorth (swedencentral is rejected by policy).
LOCATION="${LOCATION:-francecentral}"
ACR_NAME="${ACR_NAME:-aicropdoctoracr}"
CONTAINER_ENV="${CONTAINER_ENV:-ai-crop-doctor-env}"
APP_NAME="${APP_NAME:-ai-crop-doctor-api}"
IMAGE_TAG="${IMAGE_TAG:-v1}"
CPU="${CPU:-2.0}"
MEMORY="${MEMORY:-4.0Gi}"
MIN_REPLICAS="${MIN_REPLICAS:-1}"
MAX_REPLICAS="${MAX_REPLICAS:-2}"

if [[ -z "${BUNDLE_URL:-}" ]]; then
  echo "BUNDLE_URL is required (read SAS URL of plantv_all_models_expanded_tomato.zip)." >&2
  echo "See DEPLOY.md step 1." >&2
  exit 1
fi

echo "==> Resource group $RESOURCE_GROUP ($LOCATION)"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

echo "==> Azure Container Registry $ACR_NAME"
az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Basic --admin-enabled true --output none

echo "==> Building image crop-doctor-api:$IMAGE_TAG"
# NOTE: the EUI student subscription rejects this with TasksOperationsNotAllowed.
# In that case build locally instead: docker build -t crop-doctor-api:$IMAGE_TAG .
#   az acr login -n "$ACR_NAME"
#   docker tag crop-doctor-api:$IMAGE_TAG "$ACR_NAME.azurecr.io/crop-doctor-api:$IMAGE_TAG"
#   docker push "$ACR_NAME.azurecr.io/crop-doctor-api:$IMAGE_TAG"
az acr build --registry "$ACR_NAME" --image "crop-doctor-api:$IMAGE_TAG" --file Dockerfile .

echo "==> Container Apps environment $CONTAINER_ENV"
az containerapp env create --name "$CONTAINER_ENV" --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --output none 2>/dev/null || true

ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" --output tsv)
LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)

echo "==> Container app $APP_NAME"
az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_ENV" \
  --image "$LOGIN_SERVER/crop-doctor-api:$IMAGE_TAG" \
  --registry-server "$LOGIN_SERVER" \
  --registry-username "$ACR_NAME" \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8000 \
  --ingress external \
  --transport http \
  --cpu "$CPU" \
  --memory "$MEMORY" \
  --min-replicas "$MIN_REPLICAS" \
  --max-replicas "$MAX_REPLICAS" \
  --env-vars BUNDLE_URL="$BUNDLE_URL" MODEL_DIR=/app/bundle CONFIDENCE_THRESHOLD=0.60 LOG_DIR=/tmp/logs \
  --output none

FQDN=$(az containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query "properties.configuration.ingress.fqdn" --output tsv)
echo
echo "Deployed. API base URL: https://$FQDN"
echo "Health check:          https://$FQDN/api/health"
echo "Next: set API_BASE=\"https://$FQDN\" in web/config.js and redeploy the Vercel site."
