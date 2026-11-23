# Deploying the model API on Azure Container Apps

The API container is stateless; the 1.6 GB model bundle lives in Blob Storage and is
downloaded once per replica at start-up (`BUNDLE_URL`, a read-only SAS URL).

## 0. Prerequisites

- Azure CLI logged in (`az login`) with a subscription selected (`az account set -s <id>`).
- Docker **not** required: `az acr build` builds the image in Azure.
- The bundle zip: `plantv_all_models_expanded_tomato.zip` (Drive → Milestone 3 → `final_model/`).

### Current state of the EUI / Azure for Students subscription (2026-11-23)

Infrastructure is created and paid for; the image has **not** been built yet.

| Item | Value |
| --- | --- |
| Subscription | Azure for Students `1debc16e-ad86-4909-a468-b3c5dabf4b5c` (tenant EUI.edu.eg) |
| Resource group | `rg-ai-crop-doctor` — **francecentral** |
| Storage account | `aicropdoc11231221` (Standard_LRS), container `models` |
| Bundle blob | `models/plantv_all_models_expanded_tomato.zip` |
| Read SAS | 1 year, expires 2027-11-23 — stored in `azure/.env` as `BUNDLE_URL` (git-ignored) |
| Registry | `aicropdoctoracr.azurecr.io` (Basic) — created, still empty |
| Container App | **not created** |

Subscription policies that change the steps below:

- Allowed regions are only `polandcentral`, `francecentral`, `austriaeast`, `denmarkeast`,
  `italynorth`. `swedencentral` is rejected (`RequestDisallowedByAzure`).
- `az acr build` fails with `TasksOperationsNotAllowed` — ACR Tasks are blocked for this
  subscription, so the image cannot be built in Azure. Build it locally with Docker and
  `az acr login -n aicropdoctoracr && docker push`, or ask EUI support to enable ACR Tasks.
- App Service plans cannot be created in any allowed region, so Container Apps is the
  only managed host available here.

## 1. Upload the model bundle

```bash
STORAGE=aicropdoc11231221          # already created
az storage account create -n "$STORAGE" -g rg-ai-crop-doctor -l francecentral --sku Standard_LRS
az storage container create -n models --account-name "$STORAGE" --auth-mode login
az storage blob upload -f plantv_all_models_expanded_tomato.zip \
  -c models -n plantv_all_models_expanded_tomato.zip \
  --account-name "$STORAGE" --auth-mode login --overwrite
```

Create a read-only SAS valid long enough for the project (e.g. 1 year):

```bash
EXPIRY=$(date -u -d "+365 days" +%Y-%m-%dT%H:%MZ 2>/dev/null || date -u -v+365d +%Y-%m-%dT%H:%MZ)
BUNDLE_URL=$(az storage blob generate-sas \
  --account-name "$STORAGE" -c models -n plantv_all_models_expanded_tomato.zip \
  --permissions r --expiry "$EXPIRY" --https-only -o tsv)
export BUNDLE_URL="https://$STORAGE.blob.core.windows.net/models/plantv_all_models_expanded_tomato.zip?$BUNDLE_URL"
```

## 2. Build and deploy

```bash
cd azure
BUNDLE_URL="$BUNDLE_URL" ./deploy_azure.sh
```

The script creates the resource group, an ACR, a Container Apps environment and the
app (`2 vCPU / 4 GiB`, min 1 replica so the first request is not a cold model load).
It prints the public FQDN at the end.

Sizing matters: CLIP ViT-L/14-336 + DINOv2-large in float32 need roughly 3 GB of RAM.
`1 vCPU / 2 GiB` will OOM during model load.

## 3. Smoke test

```bash
API="https://<fqdn>"
curl -s "$API/api/health" | python -m json.tool     # ready: true, crops listed
curl -s -X POST "$API/api/predict" -F "file=@leaf.jpg" | python -m json.tool
```

Expected: `predictions` holds up to three `Crop___Condition` labels with confidences,
`uncertain` flips to `true` below `CONFIDENCE_THRESHOLD` (0.60).

## 4. Point the Vercel interface at it

Edit `web/config.js` → `API_BASE: "https://<fqdn>"`, commit, and let Vercel redeploy
(or set it before the first deploy). CORS is open by default; restrict it with
`CORS_ORIGINS=https://your-app.vercel.app` on the container app:

```bash
az containerapp update -n ai-crop-doctor-api -g rg-ai-crop-doctor \
  --set-env-vars CORS_ORIGINS=https://your-app.vercel.app
```

## Alternative: Azure ML managed online endpoint

If the course requires Azure ML specifically, register the bundle as a model asset,
then deploy a `ManagedOnlineEndpoint` with a custom `score.py` that reuses
`extract_features`/`run_head` from `main.py` (`init()` loads the bundle, `run()` returns
the same JSON). Container Apps is simpler here because the image, health probe and
scale rules are all in this folder.

## Cost / cleanup

```bash
az group delete -n rg-ai-crop-doctor --yes --no-wait
```

## What is not implemented in this API

- Grad-CAM: the response returns `"gradcam": null` and the UI hides the heat-map toggle.
- ONNX/INT8 export and latency benchmarking (Milestone 3 deliverables) are not part of
  this bundle; it runs the PyTorch encoders directly.
