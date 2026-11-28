# Deploying the model API on Azure Container Apps

The API container is stateless. Model weights are downloaded once per replica at
start-up from the private Hugging Face repo `omarwalied/ai-crop-doctor-weights`
(folder `balsample`, about 199 MB), using a read token stored as a Container App
secret. The earlier plan used a 1.6 GB bundle zip in Blob Storage; that bundle is the
previous CLIP + DINOv2 model and is no longer the target.

## 0. Prerequisites

- Azure CLI logged in (`az login`) with a subscription selected (`az account set -s <id>`).
- Docker is not required for the build if ACR Tasks are enabled (they are blocked here,
  see below).
- A Hugging Face read token with access to the private weights repo.

### State of the EUI / Azure for Students subscription (28 November 2026)

| Item | Value |
| --- | --- |
| Subscription | Azure for Students `1debc16e-ad86-4909-a468-b3c5dabf4b5c` (tenant EUI.edu.eg) |
| Resource group | `rg-ai-crop-doctor`, francecentral |
| Storage account | `aicropdoc11231221` (Standard_LRS), container `models` (holds the old bundle) |
| Registry | `aicropdoctoracr.azurecr.io` (Basic), created, empty |
| Container App | not created |
| Spend so far | about $0.75 (registry) |

Subscription policies that shape the steps below:

- Allowed regions: `polandcentral`, `francecentral`, `austriaeast`, `denmarkeast`,
  `italynorth`. `swedencentral` is rejected (`RequestDisallowedByAzure`).
- `az acr build` fails with `TasksOperationsNotAllowed`: ACR Tasks are blocked for this
  subscription. Build locally with Docker and `az acr login -n aicropdoctoracr &&
  docker push`, or ask EUI support to enable ACR Tasks.
- App Service plans cannot be created in the allowed regions, so Container Apps is the
  only managed host available.

## 1. Build and push the image

```bash
cd azure
az acr login -n aicropdoctoracr
docker build -t aicropdoctoracr.azurecr.io/crop-api:final .
docker push aicropdoctoracr.azurecr.io/crop-api:final
```

## 2. Create the Container App

Sizing matters: the three encoders in float32 need roughly 3 to 4 GiB of RAM.
1 vCPU / 2 GiB will run out of memory during model load.

```bash
az containerapp env create -n aicropdoctor-env -g rg-ai-crop-doctor -l francecentral

az containerapp create -n ai-crop-doctor-api -g rg-ai-crop-doctor \
  --environment aicropdoctor-env \
  --image aicropdoctoracr.azurecr.io/crop-api:final \
  --registry-server aicropdoctoracr.azurecr.io \
  --cpu 2 --memory 4Gi \
  --min-replicas 0 --max-replicas 2 \
  --target-port 8000 --ingress external \
  --secrets hf-token="$HF_TOKEN" \
  --env-vars HF_TOKEN=secretref:hf-token MODEL_DIR=/models
```

`--min-replicas 0` means the app scales to zero when nobody is using it, so the cost is
close to nothing at rest. The first request after a quiet period waits for the replica
to start and load the weights, which takes about a minute.

## 3. Smoke test

```bash
API="https://<fqdn>"
curl -s "$API/api/health" | python -m json.tool
curl -s -X POST "$API/api/predict" -F "file=@leaf.jpg" | python -m json.tool
```

Expected: `predictions` holds up to three `Crop___Condition` labels with confidences,
and `uncertain` turns true below `CONFIDENCE_THRESHOLD` (0.60).

## 4. Point the web interface at it

Edit `web/config.js` so `API_BASE` is the Container App URL, commit, and let Vercel
redeploy. CORS is open by default; restrict it with:

```bash
az containerapp update -n ai-crop-doctor-api -g rg-ai-crop-doctor \
  --set-env-vars CORS_ORIGINS=https://your-app.vercel.app
```

## Cost and cleanup

```bash
az group delete -n rg-ai-crop-doctor --yes --no-wait
```

## What the API does not do

- Grad-CAM: the response returns `gradcam: null` and the UI hides the heat-map toggle.
- ONNX / INT8 export and latency benchmarking: not implemented. The service runs the
  PyTorch encoders directly, about 25 seconds per photo on CPU.
