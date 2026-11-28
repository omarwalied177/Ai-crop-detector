# AI Crop Doctor - Multi-Crop Plant Disease Diagnosis System

[![CI](https://github.com/omarwalied177/Ai-crop-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/omarwalied177/Ai-crop-detector/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-ee4c2c.svg)](https://pytorch.org/)

AI Crop Doctor names the crop and the likely disease from a single leaf photo. A crop
router picks one of 12 crops, then that crop's disease head names the condition.
Features come from three frozen vision encoders; only the small heads and a LoRA
adapter are trained.

---

## Final model (28 November 2026)

| | |
|---|---|
| Encoders | CLIP ViT-L/14-336, DINOv2-Large with LoRA (r=8, alpha=16, on query and value), SigLIP-so400m-384. Frozen, apart from the LoRA adapter on DINOv2. |
| Heads | 12-crop router plus one disease head per crop: 11 heads, because Squash has no disease head. |
| Training pool | 53 crop+disease classes across 12 crops. |
| Class balance | Sampling balanced by class, source and image group (the `balsample` variant). |
| Weights | Private Hugging Face repo `omarwalied/ai-crop-doctor-weights`, folder `balsample`, about 199 MB: `router.pt`, 11 head checkpoints, `dinov2_lora_state.pt`, `config.json`, `class_lists.json`. |

Held-out test accuracy, balanced-sampling run:

| Test set | Accuracy |
|---|---|
| PlantVillage (lab backgrounds) | 99.2% |
| PlantDoc (natural backgrounds) | 86.9% |
| PlantSeg unseen (field photos) | 85.6% |

Scores are on the images each test set holds for the classes the model supports, so
the scored count is smaller than the raw set size.

Reading these numbers:

- Three other class-balance recipes (class weights, no balancing, the earlier v6 run)
  landed within about 1.5 points on every set. The gap between them is noise, so
  balanced sampling was kept mainly because it was best on the unseen field set.
- The one clear gain from retraining the feature extractor is potato late blight,
  82% versus 71% before, on 14 test photos.
- The field test sets are small. One photo moves a class score by several points, so
  read 86-87% as an estimate. The model has not yet been tested on a fresh set of
  photos that nobody tuned on.
- Weakest classes: blueberry rust 61%, grape leaf spot 64%, potato late blight 75%,
  cherry leaf spot 76%, grape downy mildew 77%. Several small classes have under 80
  training photos and are candidates for a "not supported" label.

Details and provenance: [`reports/final_model_results.md`](reports/final_model_results.md).

---

## How it works

```
leaf photo
   │
   ▼
CLIP-L/336 + DINOv2-L (LoRA) + SigLIP-384   frozen encoders
   │
   ▼
crop router (12 crops)
   │
   ▼
disease head of that crop (11 heads)
   │
   ▼
top-3 conditions with confidences, or "not sure"
```

- Crop confidence below 0.35: the photo is reported as not diagnosed instead of
  running a disease head on a guess.
- Top disease confidence below 0.60: the answer is flagged `uncertain`.
- Grad-CAM is not produced: the encoders are frozen, so there is no useful gradient
  path to the input.

---

## Repository layout

```
.
├── .github/workflows/ci.yml   CI: compile the API, run the health probe in demo mode
├── azure/                     FastAPI service and Azure deployment files
│   ├── main.py                API: /api/health, /api/predict, /api/feedback
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── deploy_azure.sh        Azure Container Apps deployment script
│   ├── DEPLOY.md              Step-by-step deployment guide
│   └── .env.example
├── web/                       Static frontend (EN/AR, light/dark)
│   ├── index.html
│   ├── config.js              API_BASE and UI settings
│   ├── css/styles.css
│   ├── js/api.js, app.js, i18n.js
│   ├── data/knowledge_base.json
│   └── tools/build_kb.py
├── streamlit_app/             Streamlit UI demo (no model connected)
│   ├── app.py
│   ├── i18n.js
│   ├── samples/               11 PlantVillage sample photos
│   └── requirements.txt
├── notebooks/
│   ├── 2_Model_Development_Evaluation.ipynb
│   └── 4_Final_Heads_Expansion.ipynb
└── reports/
    ├── m2_final_report.json
    ├── test_classification_report.csv
    ├── test_per_crop_metrics.csv
    └── final_model_results.md
```

---

## API

### `GET /api/health`
Readiness, whether weights are loaded, and the list of supported crops.

### `POST /api/predict`
Multipart form upload, field `file` (JPEG, PNG or WebP, up to 10 MB). Optional field
`known_crop`.

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
    {"class_id": 1, "label": "Tomato___Late_blight", "confidence": 0.8924},
    {"class_id": 0, "label": "Tomato___Early_blight", "confidence": 0.0811},
    {"class_id": 2, "label": "Tomato___healthy", "confidence": 0.0265}
  ],
  "status": "ok",
  "note": null,
  "preprocess": {
    "input": {"width": 1200, "height": 1600, "mode": "RGB"},
    "steps": [
      {"id": "decode", "label": "RGB decode and EXIF orientation", "detail": "1200x1600 RGB"},
      {"id": "clip_resize", "label": "CLIP bicubic resize", "detail": "336x336"}
    ]
  },
  "gradcam": null
}
```

### `POST /api/feedback`
Accepts a "was this correct?" payload. It is written to the service log only.

---

## Run locally

```bash
git clone https://github.com/omarwalied177/Ai-crop-detector.git
cd Ai-crop-detector

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r azure/requirements.txt

python -m uvicorn azure.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Without model weights the service starts in demo mode
(deterministic dummy predictions) so the UI and the API contract can be tested.

Model files are not in the repository. Download the `balsample` folder from the
private Hugging Face repo `omarwalied/ai-crop-doctor-weights` and point `MODEL_DIR`
at it. See [`azure/DEPLOY.md`](azure/DEPLOY.md).

---

## Deployment status

| Target | State |
|---|---|
| Streamlit UI demo | Live at https://ai-crop-doctor-omar.streamlit.app/. UI only: no model is connected, so it shows no diagnosis. |
| Azure Container Apps | Approved and scripted (`azure/deploy_azure.sh`), not deployed. Scale-to-zero, 2 vCPU / 4 GiB. |
| Hugging Face Space | Not possible on the free plan: Gradio and Docker Spaces need a paid plan. |

`azure/main.py` implements the API contract and loads the previous model bundle
(CLIP + DINOv2, before SigLIP and LoRA). The container that serves the final weights
is the one being deployed to Azure.

---

## Model history: why the older documents mention two model families

- **Milestone 2 (October 2026):** MobileNetV3Large, 38 classes, 98.6% on a held-out
  PlantVillage-style split at 128x128. This was a lab benchmark built to satisfy the
  milestone, not field performance, and it is kept in the Drive milestone folder.
- **Milestones 3-5 (October-November 2026):** the frozen-encoder design, first with
  CLIP + DINOv2 only. The Milestone 5 deck reports that run: PlantWild 85.1%,
  PlantDoc 80.6%, PlantVillage 99.6%.
- **Final (28 November 2026):** the same design with SigLIP added and a LoRA adapter
  on DINOv2, trained with balanced sampling. This is the model in the table above and
  the one the deployment targets.

The earlier numbers were not wrong for the model they measured. They are simply older.
