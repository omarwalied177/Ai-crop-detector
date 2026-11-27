# AI Crop Doctor — Multi-Crop Plant Disease Diagnosis System

[![CI](https://github.com/omarwalied177/Ai-crop-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/omarwalied177/Ai-crop-detector/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-ee4c2c.svg)](https://pytorch.org/)

AI Crop Doctor is an intelligent plant disease diagnosis system that accurately identifies crop species and their diseases from a single leaf photograph. Built with high-capacity vision foundation encoders (**CLIP ViT-L/14-336** + **DINOv2-Large**), a hierarchical 12-crop router, and per-crop disease classification heads.

---

## Key Features

- **Hierarchical Classification**: A two-stage pipeline first routes the leaf image to the predicted crop species, then applies a crop-specific disease head.
- **Foundation Vision Encoders**: Leverages frozen features from CLIP (336px) and DINOv2 (224px) for robust feature representation across diverse lighting and leaf angles.
- **Interactive Bilingual Web Interface**: Plain HTML5/CSS3/JavaScript frontend with zero build step, supporting both **Arabic (العربية)** and **English** with full RTL layout.
- **Transparent Preprocessing Inspector**: Displays the exact image transformations applied during inference (PIL decode, bicubic resize, normalization, and view augmentation) with visual thumbnails.
- **Rich Disease Knowledge Base**: Comprehensive offline knowledge base with 38+ plant conditions, symptoms, and organic/chemical treatments in both languages.
- **Dual Deployment Options**:
  - Run as a single unified service (FastAPI serving both REST API and web UI).
  - Or decouple into Azure Container Apps (Backend) + Vercel (Frontend).
- **Graceful Fallback Mode**: Starts in dummy mode if the 1.6 GB model weights bundle is not yet downloaded, enabling instant local testing and CI verification.

---

## System Architecture

```
                       ┌─────────────────────────────────────┐
                       │       Web Client (Browser)          │
                       │   Bilingual UI (AR / EN) · Top-3    │
                       │ Preprocessing Pipeline Inspector· KB│
                       └──────────────────┬──────────────────┘
                                          │ POST /api/predict
                                          ▼
                       ┌─────────────────────────────────────┐
                       │     FastAPI Backend (azure/main.py) │
                       │    Unified Server or Container App  │
                       └─────────┬───────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌───────────────────┐           ┌───────────────────┐
       │ CLIP ViT-L/14-336 │           │   DINOv2-Large    │
       │  (Vision Tower)   │           │  (Patch Features) │
       └─────────┬─────────┘           └─────────┬─────────┘
                 └───────────────┬───────────────┘
                                 ▼
                 ┌───────────────────────────────┐
                 │     Hierarchical Router       │
                 │   12-Crop Species Classifier  │
                 └───────────────┬───────────────┘
                                 ▼
                 ┌───────────────────────────────┐
                 │   Per-Crop Disease Heads      │
                 │ Tomato, Potato, Apple, Corn...│
                 └───────────────────────────────┘
```

---

## Repository Structure

```
.
├── .github/workflows/
│   └── ci.yml               # Automated CI (lint, compile, health check)
├── azure/                   # FastAPI backend & deployment files
│   ├── main.py              # Core service (inference, router, dummy fallback)
│   ├── requirements.txt     # Python backend dependencies
│   ├── Dockerfile           # Optimized container image (CPU PyTorch)
│   ├── deploy_azure.sh      # Deployment script for Azure Container Apps
│   ├── DEPLOY.md            # Step-by-step cloud deployment instructions
│   ├── .dockerignore
│   └── .env.example         # Environment template (no secrets committed)
├── web/                     # Frontend web application (Vercel ready)
│   ├── index.html           # Main UI structure
│   ├── config.js            # Frontend configuration (API endpoint)
│   ├── css/styles.css       # Responsive design, light/dark accents, RTL
│   ├── js/
│   │   ├── api.js           # API communication & error handling
│   │   ├── app.js           # UI logic & preprocessing renderer
│   │   ├── i18n.js          # Arabic and English translations
│   │   └── kb-data.js       # Bundled disease data
│   ├── data/knowledge_base.json
│   └── tools/build_kb.py    # Script to regenerate knowledge base data
├── notebooks/               # Research & training notebooks
│   ├── 1_PlantVillage_Full_Pipeline.ipynb
│   ├── 2_Model_Development_Evaluation.ipynb
│   ├── 3_Robustness_Explainability_Cloud.ipynb
│   └── 4_Final_Heads_Expansion.ipynb
└── reports/                 # Evaluation metrics, confusion matrix & proposal
    ├── test_confusion_matrix.png
    ├── m2_final_report.json
    ├── test_classification_report.csv
    ├── test_per_crop_metrics.csv
    └── AI_Crop_Doctor_Project_Proposal.pdf
```

---

## Quick Start

### 1. Local Run (FastAPI + Web UI Together)

Clone the repository and install requirements:

```bash
git clone https://github.com/omarwalied177/Ai-crop-detector.git
cd AI_Crop_Doctor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies (CPU PyTorch first)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r azure/requirements.txt
```

Run the application:

```bash
python -m uvicorn azure.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at **http://127.0.0.1:8000**.
*Note: If the 1.6 GB model weights bundle is not present, the service automatically runs in simulated dummy mode so you can test all UI workflows and API endpoints immediately.*

---

## Model Bundle Setup

The complete multi-crop model bundle is **`plantv_all_models_expanded_tomato.zip`** (~1.5 GB). Due to GitHub storage limits, model checkpoints are stored in external object storage.

| Source | Setup Instruction |
|---|---|
| **Local Folder** | Extract the zip to `./bundle` (or set `MODEL_DIR=/path/to/extracted_bundle`) |
| **Local Zip** | Place `plantv_all_models_expanded_tomato.zip` next to `azure/main.py` |
| **Azure Blob** | Set `BUNDLE_URL="https://<account>.blob.core.windows.net/.../bundle.zip?<sas>"` |

On first launch, the service automatically converts float16 weights to float32 for fast CPU inference.

---

## Cloud Deployment

### Backend on Azure Container Apps

The backend container image can be built and deployed via Azure Container Registry (ACR) and Container Apps:

```bash
cd azure
chmod +x deploy_azure.sh
./deploy_azure.sh
```

For full details, environment variables, and scaling configuration, see [`azure/DEPLOY.md`](azure/DEPLOY.md).

### Frontend on Vercel

1. Log in to [Vercel](https://vercel.com/) and click **Add New Project**.
2. Import this repository and configure:
   - **Root Directory**: `web`
   - **Framework Preset**: `Other` (no build command needed)
3. Update `web/config.js` to point `API_BASE` to your deployed Azure Container App URL:
   ```javascript
   API_BASE: "https://your-app-name.<region>.azurecontainerapps.io"
   ```

---

## API Documentation

### Health Probe
`GET /api/health`
Returns readiness status, whether model weights are loaded, and the list of supported crops.

### Predict Disease
`POST /api/predict`
Multipart form upload with field `file` (JPEG, PNG, WebP ≤ 10 MB). Optional field `known_crop`.

**Sample Response:**
```json
{
  "request_id": "7f8b91cd-4011-4b2a-892f-bfae0dc8b3b1",
  "model_version": "multicrop-clip-dino-v1",
  "latency_ms": 780,
  "uncertain": false,
  "predicted_crop": "Tomato",
  "crop_confidence": 0.9854,
  "routed_crop": "Tomato",
  "predictions": [
    {
      "class_id": 1,
      "label": "Tomato___Late_blight",
      "confidence": 0.8924
    },
    {
      "class_id": 0,
      "label": "Tomato___Early_blight",
      "confidence": 0.0811
    },
    {
      "class_id": 2,
      "label": "Tomato___healthy",
      "confidence": 0.0265
    }
  ],
  "status": "ok",
  "note": null,
  "preprocess": {
    "input": {
      "width": 1200,
      "height": 1600,
      "mode": "RGB"
    },
    "steps": [
      {
        "id": "decode",
        "label": "RGB decode & EXIF orientation",
        "detail": "1200×1600 RGB",
        "preview": "data:image/jpeg;base64,..."
      },
      {
        "id": "clip_resize",
        "label": "CLIP bicubic resize",
        "detail": "336×336",
        "preview": "data:image/jpeg;base64,..."
      }
    ]
  }
}
```

---

## Evaluation & Results

Evaluation metrics and confusion matrices across crops are available in the [`reports/`](reports/) directory:
- **Accuracy & F1**: >95% macro F1 across diagnosed crop classes.
- **Confusion Matrix**: [`reports/test_confusion_matrix.png`](reports/test_confusion_matrix.png).
- **Per-Crop Breakdown**: [`reports/test_per_crop_metrics.csv`](reports/test_per_crop_metrics.csv).

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
