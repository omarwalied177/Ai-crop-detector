"""
AI Crop Doctor – Merged Backend (FastAPI)
=========================================
Serves both the REST API and the static frontend.

Model
-----
The best model bundle `plantv_all_models_expanded_tomato.zip`
(frozen CLIP ViT-L/14-336 + DINOv2-large encoders, a 12-crop router and
per-crop disease heads with the expanded Tomato head) is loaded directly by
this service. If the extracted bundle is absent but the zip is reachable, the
needed members are extracted once into `bundle/` on start-up.

Endpoints
---------
  GET  /api/health      – liveness probe (+ loaded crops)
  POST /api/predict     – multipart/form-data, field "file" (JPEG / PNG / WebP)
                          optional field "known_crop" (e.g. "Tomato")
  POST /api/feedback    – application/json (optional)
  GET  /*               – static frontend (index.html + assets)

API contract (matches what frontend/config.js and js/api.js expect)
--------------------------------------------------------------------
  POST /api/predict → {
    "request_id":    "<uuid>",
    "model_version": "multicrop-clip-dino-v1",
    "latency_ms":    <int>,
    "uncertain":     <bool>,        # true when top confidence < CONFIDENCE_THRESHOLD
    "predictions":   [
      {"class_id": <int>, "label": "<class_name>", "confidence": <float 0-1>},
      ...                           # top 3, sorted descending by confidence
    ],
    "predicted_crop":   "<crop>",   # extra: crop-router result
    "crop_confidence":  <float>,
    "routed_crop":      "<crop>",
    "status":           "ok",       # ok | single_class_crop | low_crop_confidence
                                    #   | unsupported_crop | dummy
    "note":             null,
    "preprocess": {                 # the applied training-time pipeline, step by step
      "input": {"width": 1200, "height": 1600, "mode": "RGB", "format": "JPEG",
                "exif_orientation": 1},
      "steps": [{"id": "decode|clip_resize|dino_resize|normalize|features|views",
                 "label": "<short name>", "detail": "<what was applied>",
                 "preview": "data:image/jpeg;base64,..."}],   # preview may be null
      "recipe": {"resize": "PIL bicubic direct resize", "clip_size": 336,
                 "dino_size": 224, "views": "original + horizontal flip",
                 "feature_mode": "mean_patch|topk_norm", "topk": 0}
    },
    "gradcam": null                 # Grad-CAM is not produced by this bundle
  }

Environment
-----------
  MODEL_DIR             extracted bundle directory (default: ./bundle)
  BUNDLE_ZIP            zip to extract when MODEL_DIR has no bundle
                        (default: looked up next to this file, then in the Drive
                        Milestone 3 final_model folder)
  CONFIDENCE_THRESHOLD  below this → uncertain=True (default 0.60)
  MAX_UPLOAD_MB         upload limit (default 10)
  TOP_N                 number of predictions returned (default 3)
  MIN_CROP_CONFIDENCE   crop-router confidence below which no disease is
                        diagnosed (default 0.35)
  MODEL_VERSION         string reported in responses
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import time
import traceback
import tempfile
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from safetensors import safe_open
from torch import nn
from torch.nn import functional as F
from transformers import AutoModel, CLIPVisionModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("crop_doctor")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
FRONTEND_DIR = None
for candidate in [HERE / "web", HERE.parent / "web", HERE / "frontend", HERE.parent / "frontend"]:
    if candidate.exists() and (candidate / "index.html").exists():
        FRONTEND_DIR = candidate
        break
if FRONTEND_DIR is None:
    FRONTEND_DIR = HERE / "web"

MODEL_DIR = Path(os.getenv("MODEL_DIR", str(HERE / "bundle")))
BUNDLE_ZIP_NAME = "plantv_all_models_expanded_tomato.zip"
BUNDLE_ZIP = os.getenv("BUNDLE_ZIP", "").strip()

CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.60"))
# Stage 0 gate: below this crop-router confidence the crop is not trusted, so the
# service reports "not diagnosed" instead of running a disease head on a guess.
MIN_CROP_CONFIDENCE = float(os.getenv("MIN_CROP_CONFIDENCE", "0.35"))
MAX_BYTES = int(float(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024)
TOP_N = int(os.getenv("TOP_N", "3"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "multicrop-clip-dino-v1")


# ---------------------------------------------------------------------------
# Bundle location / extraction
# ---------------------------------------------------------------------------
def find_bundle_root(root: Path) -> Optional[Path]:
    """Return the directory holding config.json AND crop_head.pt.

    The encoders ship their own clip/config.json and dino/config.json, so a plain
    rglob("config.json") would pick the wrong directory.
    """
    if not root.exists():
        return None
    for candidate in root.rglob("config.json"):
        if (candidate.parent / "crop_head.pt").exists():
            return candidate.parent
    return None


def locate_bundle_zip() -> Optional[Path]:
    """Find the model bundle zip: explicit env var, then the Drive folders."""
    if BUNDLE_ZIP:
        p = Path(BUNDLE_ZIP)
        return p if p.is_file() else None

    candidates = [
        HERE / BUNDLE_ZIP_NAME,
        HERE / "models" / BUNDLE_ZIP_NAME,
    ]
    for parent in list(HERE.parents)[:3]:
        candidates.append(parent / BUNDLE_ZIP_NAME)
        try:
            candidates.extend(sorted(parent.glob(f"3_*/final_model/{BUNDLE_ZIP_NAME}")))
        except OSError:
            pass
    for p in candidates:
        if p.is_file():
            return p
    return None


def extract_bundle(zip_path: Path, target: Path) -> None:
    """Extract only what inference needs (configs, encoders, heads) from the zip."""
    target.mkdir(parents=True, exist_ok=True)
    log.info("Extracting model bundle %s → %s (first start only)…", zip_path, target)
    with zipfile.ZipFile(zip_path) as zf:
        members = [
            m for m in zf.infolist()
            if not m.is_dir()
            and (
                m.filename.lower().endswith("/config.json")
                or m.filename.lower().endswith(".pt")
                or m.filename.lower().endswith(".safetensors")
            )
        ]
        total = sum(m.file_size for m in members) / (1024 * 1024)
        log.info("Extracting %d files (%.0f MB)…", len(members), total)
        zf.extractall(target, members=members)
    log.info("Bundle extracted into %s", target)


# ---------------------------------------------------------------------------
# Heads
# ---------------------------------------------------------------------------
def ensure_fp32_weights(root: Path) -> None:
    """The shipped encoder safetensors are float16.

    float16 inference on CPU is ~5x slower here, and up-casting both encoders in
    RAM at load time overflows this machine's per-process memory limit (it
    segfaults). So each file is rewritten once as float32 (the fp16 original is
    kept as model.fp16.safetensors) before the encoders are loaded.
    """
    from safetensors.torch import load_file, save_file

    for name in ("clip", "dino"):
        cfg_path = root / name / "config.json"
        if not cfg_path.exists():
            continue
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if cfg.get("dtype") in (None, "float32", "float"):
            continue

        weights = root / name / "model.safetensors"
        backup = root / name / "model.fp16.safetensors"
        if not backup.exists() and weights.exists():
            weights.rename(backup)
        if not backup.exists():
            continue

        log.info("Converting %s encoder weights to float32 (one-off)…", name)
        save_file({k: v.float() for k, v in load_file(str(backup)).items()}, str(weights))
        cfg["dtype"] = "float32"
        if "torch_dtype" in cfg:
            cfg["torch_dtype"] = "float32"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _from_pretrained(model_cls, path: Path, dtype: torch.dtype, device: str):
    """Load on CPU in the wanted dtype (transformers 5 uses `dtype`, 4.x `torch_dtype`)."""
    try:
        model = model_cls.from_pretrained(str(path), local_files_only=True, dtype=dtype)
    except TypeError:
        model = model_cls.from_pretrained(str(path), local_files_only=True, torch_dtype=dtype)
    return model.to(device).eval()


def make_head(dim: int, k: int, head_cfg: dict) -> nn.Module:
    if head_cfg["hidden"] == 0:
        return nn.Sequential(nn.Dropout(head_cfg["in_drop"]), nn.Linear(dim, k))
    return nn.Sequential(
        nn.Dropout(head_cfg["in_drop"]),
        nn.Linear(dim, head_cfg["hidden"]),
        nn.GELU(),
        nn.Dropout(head_cfg["drop2"]),
        nn.Linear(head_cfg["hidden"], k),
    )


def load_head_checkpoint(path: Path, feature_dim: int, device: str) -> dict:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    names = sorted(checkpoint["class_to_idx"], key=checkpoint["class_to_idx"].get)
    model = make_head(feature_dim, len(names), checkpoint["cfg"]).to(device)
    model.load_state_dict(checkpoint["state"])
    model.eval()
    return {
        "model": model,
        "names": names,
        "mu": checkpoint["mu"].float().to(device),
        "sd": checkpoint["sd"].float().to(device),
    }


# ---------------------------------------------------------------------------
# Model bundle
# ---------------------------------------------------------------------------
class ModelBundle:
    def __init__(self, root: Path):
        self.root = root
        self.config = json.loads((root / "config.json").read_text(encoding="utf-8"))
        self.recipe = self.config["recipe"]
        self.feature_dim = int(self.config["feature_dim"])
        # v1 bundles pool DINO patches with the mean; v2 bundles keep the top-k
        # highest-norm patches, which preserves the lesion instead of averaging it away.
        self.feature_mode = str(self.config.get("feature_mode", "mean_patch"))
        self.topk = int(self.config.get("topk", 0) or 0)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32

        log.info("Loading encoders from %s on %s", root, self.device)
        # Vision tower only: the CLIP text tower is not used for inference and
        # costs ~0.5 GB, which this machine cannot spare on top of DINOv2-large.
        self.clip = _from_pretrained(CLIPVisionModel, root / "clip", self.dtype, self.device)
        with safe_open(str(root / "clip" / "model.safetensors"), framework="pt") as f:
            self.clip_projection = f.get_tensor("visual_projection.weight").to(self.device, dtype=self.dtype)
        self.dino = _from_pretrained(AutoModel, root / "dino", self.dtype, self.device)
        self.clip.requires_grad_(False)
        self.dino.requires_grad_(False)

        self.clip_mean = torch.tensor(self.recipe["clip_mean"], device=self.device, dtype=self.dtype).view(1, 3, 1, 1)
        self.clip_std = torch.tensor(self.recipe["clip_std"], device=self.device, dtype=self.dtype).view(1, 3, 1, 1)
        self.dino_mean = torch.tensor(self.recipe["dino_mean"], device=self.device, dtype=self.dtype).view(1, 3, 1, 1)
        self.dino_std = torch.tensor(self.recipe["dino_std"], device=self.device, dtype=self.dtype).view(1, 3, 1, 1)

        self.crop_head = load_head_checkpoint(root / "crop_head.pt", self.feature_dim, self.device)

        self.disease_heads: dict[str, dict] = {}
        for crop, relative in self.config.get("disease_heads", {}).items():
            self.disease_heads[crop] = load_head_checkpoint(root / relative, self.feature_dim, self.device)

        # Stage 0: `disease_heads` is authoritative. The old `tomato_experiment`
        # override (which swapped in the 3-class tv_pd head) is deliberately not
        # applied any more - the 6-class Tomato_expanded head is served instead.
        # The extra heads stay in `tomato_heads` for reference only.
        if "Tomato" not in self.disease_heads:
            log.warning("Bundle has no Tomato disease head; tomato will be unsupported.")

        # Crops whose only known condition is a single class (e.g. Blueberry___healthy).
        self.single_class = {
            crop: labels[0] for crop, labels in self.config.get("single_class_crops", {}).items() if labels
        }
        self.crop_names = list(self.crop_head["names"])
        log.info("Bundle ready: crops=%s heads=%s feature_mode=%s topk=%s", self.crop_names, list(self.disease_heads), self.feature_mode, self.topk)

    @torch.inference_mode()
    def preprocess(self, image: Image.Image) -> dict:
        """Build exactly the encoder inputs used in training.

        The training recipe is `resize='PIL bicubic direct resize'` with the
        `original` and `horizontal flip` views; this method is the single place
        where serving applies it, and it also keeps the intermediates so the UI
        can show what the model actually received.
        """
        rgb = ImageOps.exif_transpose(image).convert("RGB")

        clip_size = int(self.recipe["clip_size"])
        clip_img = rgb.resize((clip_size, clip_size), Image.Resampling.BICUBIC)
        x_clip = torch.from_numpy(np.asarray(clip_img).copy()).permute(2, 0, 1).unsqueeze(0)
        x_clip = x_clip.to(self.device, dtype=self.dtype)
        x_clip = (x_clip / 255.0 - self.clip_mean) / self.clip_std

        dino_size = int(self.recipe["dino_size"])
        dino_img = rgb.resize((dino_size, dino_size), Image.Resampling.BICUBIC)
        x_dino = torch.from_numpy(np.asarray(dino_img).copy()).permute(2, 0, 1).unsqueeze(0)
        x_dino = x_dino.to(self.device, dtype=self.dtype)
        x_dino = (x_dino / 255.0 - self.dino_mean) / self.dino_std

        return {
            "clip": x_clip,
            "dino": x_dino,
            "clip_img": clip_img,
            "dino_img": dino_img,
            "rgb": rgb,
            "source_size": image.size,
            "source_mode": image.mode,
            "source_format": image.format,
            "exif_orientation": int(image.getexif().get(274, 1) or 1),
        }

    @torch.inference_mode()
    def encode(self, prep: dict) -> torch.Tensor:
        """(1, 2 views, 2816) features: CLIP image embedding + DINOv2 CLS/mean tokens."""
        x_clip = prep["clip"]
        clip_views = []
        for view in (x_clip, torch.flip(x_clip, [3])):
            pooled = self.clip(pixel_values=view).pooler_output
            embedded = F.linear(pooled, self.clip_projection.to(pooled.dtype))
            clip_views.append(F.normalize(embedded.float(), dim=-1))

        x_dino = prep["dino"]
        dino_views = []
        for view in (x_dino, torch.flip(x_dino, [3])):
            hidden = self.dino(pixel_values=view).last_hidden_state
            patches = hidden[:, 1:]
            if self.feature_mode == "topk_norm" and self.topk > 0:
                k = min(self.topk, patches.shape[1])
                idx = patches.norm(dim=-1).topk(k, dim=-1).indices
                patch_pool = patches.gather(1, idx[..., None].expand(-1, -1, patches.shape[-1])).mean(1)
            else:
                patch_pool = patches.mean(1)
            dino_views.append(torch.cat([hidden[:, 0], patch_pool], dim=-1).float())

        clip_feat = torch.stack(clip_views, dim=1)   # (1, 2, 768)
        dino_feat = torch.stack(dino_views, dim=1)   # (1, 2, 2048)
        return torch.cat([clip_feat, dino_feat], dim=-1)

    @torch.inference_mode()
    def features(self, image: Image.Image) -> torch.Tensor:
        """Preprocess + encode in one call (kept for callers that only need features)."""
        return self.encode(self.preprocess(image))

    @torch.inference_mode()
    def run_head(self, head: dict, feat: torch.Tensor, top_n: int | None = None) -> list[dict]:
        x = (feat - head["mu"]) / head["sd"]
        logits = head["model"](x).mean(dim=1)
        probs = torch.softmax(logits, dim=-1)[0].cpu().numpy()
        order = np.argsort(-probs)[: top_n or TOP_N]
        return [
            {"index": int(i), "label": head["names"][int(i)], "confidence": round(float(probs[int(i)]), 4)}
            for i in order
        ]

    def classify(self, image: Image.Image, known_crop: Optional[str] = None) -> dict:
        prep = self.preprocess(image)
        feat = self.encode(prep)

        crop_top = self.run_head(self.crop_head, feat, TOP_N)
        predicted_crop = crop_top[0]["label"]
        crop_confidence = crop_top[0]["confidence"]
        routed_crop = (
            known_crop
            if (known_crop and (known_crop in self.disease_heads or known_crop in self.single_class))
            else predicted_crop
        )

        note = None
        status = "ok"
        predictions: list[dict] = []
        unknown_label = f"{routed_crop}___Unknown"

        # Stage 0 (honesty): a crop prior is not a diagnosis, and a crop without a
        # trained head must never be reported as "healthy".
        crop_untrusted = known_crop is None and crop_confidence < MIN_CROP_CONFIDENCE

        if crop_untrusted:
            status = "low_crop_confidence"
            note = "crop_not_confident_no_diagnosis"
            predictions = [{"index": -1, "label": unknown_label, "confidence": 0.0}]
        elif routed_crop in self.disease_heads:
            predictions = self.run_head(self.disease_heads[routed_crop], feat, TOP_N)
        elif routed_crop in self.single_class:
            # The crop is known, but the model only ever saw one condition for it:
            # this is the dataset prior, not a verified diagnosis.
            predictions = [
                {"index": 0, "label": self.single_class[routed_crop], "confidence": round(crop_confidence, 4)}
            ]
            note = "single_class_crop"
            status = "single_class_crop"
        else:
            status = "unsupported_crop"
            note = "no_trained_disease_head_for_crop"
            predictions = [{"index": -1, "label": unknown_label, "confidence": 0.0}]

        top_confidence = predictions[0]["confidence"] if predictions else 0.0
        return {
            "predicted_crop": predicted_crop,
            "crop_confidence": round(crop_confidence, 4),
            "routed_crop": routed_crop,
            "predictions": predictions,
            "uncertain": status in ("low_crop_confidence", "unsupported_crop")
            or top_confidence < CONFIDENCE_THRESHOLD,
            "status": status,
            "note": note,
            "preprocess": preprocess_report(prep, self.recipe, self.feature_mode, self.topk),
        }


# ---------------------------------------------------------------------------
# Preprocessing report (what the UI shows between upload and prediction)
# ---------------------------------------------------------------------------
def _data_url(image: Image.Image, size: int = 192, quality: int = 80) -> str:
    thumb = image.convert("RGB").copy()
    thumb.thumbnail((size, size), Image.Resampling.BICUBIC)
    buf = io.BytesIO()
    thumb.save(buf, "JPEG", quality=quality, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _tensor_data_url(x: torch.Tensor, size: int = 192) -> str:
    """Show the normalised tensor literally: values are clipped into 0-1 for viewing."""
    arr = (x.detach().float().clamp(0, 1) * 255).round().to(torch.uint8).permute(1, 2, 0).cpu().numpy()
    return _data_url(Image.fromarray(np.ascontiguousarray(arr), "RGB"), size)


def preprocess_report(prep: dict, recipe: dict, feature_mode: str, topk: int) -> dict:
    """Describe every step between the uploaded file and the model input.

    The order matches the training notebook: EXIF/decoded RGB, direct bicubic
    resize per encoder, normalisation, then the two views (original + hflip).
    """
    clip_size = int(recipe["clip_size"])
    dino_size = int(recipe["dino_size"])
    src_w, src_h = prep["source_size"]
    rgb_w, rgb_h = prep["rgb"].size
    orientation = prep["exif_orientation"]
    patch_pool = f"top-{topk} by norm" if feature_mode == "topk_norm" and topk else "mean"

    steps = [
        {
            "id": "decode",
            "label": "Decode & orient",
            "detail": f"{src_w} × {src_h} px {prep['source_mode']} → {rgb_w} × {rgb_h} px RGB"
            + (f" · EXIF orientation {orientation}" if orientation not in (0, 1) else " · no EXIF rotation"),
            "preview": _data_url(prep["rgb"]),
        },
        {
            "id": "clip_resize",
            "label": "CLIP input",
            "detail": f"{clip_size} × {clip_size} px · bicubic · no crop",
            "preview": _data_url(prep["clip_img"]),
        },
        {
            "id": "dino_resize",
            "label": "DINOv2 input",
            "detail": f"{dino_size} × {dino_size} px · bicubic · no crop",
            "preview": _data_url(prep["dino_img"]),
        },
        {
            "id": "normalize",
            "label": "Normalize",
            "detail": "÷ 255, then model mean / std (CLIP and DINOv2 use their own)",
            "preview": _tensor_data_url(prep["clip"][0]),
        },
        {
            "id": "features",
            "label": "Feature extraction",
            "detail": f"768 CLIP + 2048 DINOv2 CLS + 2048 DINOv2 patches ({patch_pool})",
            "preview": None,
        },
        {
            "id": "views",
            "label": "Views",
            "detail": "original + horizontal flip · logits averaged over both views",
            "preview": _tensor_data_url(torch.flip(prep["clip"], [3])[0]),
        },
    ]

    return {
        "input": {
            "width": src_w,
            "height": src_h,
            "mode": prep["source_mode"],
            "format": prep["source_format"],
            "exif_orientation": orientation,
        },
        "steps": steps,
        "recipe": {
            "resize": recipe.get("resize"),
            "clip_size": clip_size,
            "dino_size": dino_size,
            "views": "original + horizontal flip",
            "feature_mode": feature_mode,
            "topk": topk,
        },
    }


bundle: Optional[ModelBundle] = None
LOAD_ERROR: Optional[str] = None
try:
    _root = find_bundle_root(MODEL_DIR)
    if _root is None and BUNDLE_URL:
        download_bundle(BUNDLE_URL, MODEL_DIR)
        _root = find_bundle_root(MODEL_DIR)
    if _root is None:
        _zip = locate_bundle_zip()
        if _zip is not None:
            extract_bundle(_zip, MODEL_DIR)
            _root = find_bundle_root(MODEL_DIR)
    if _root is None:
        raise FileNotFoundError(
            f"Model bundle not found under {MODEL_DIR}. Set MODEL_DIR to the extracted bundle "
            f"or BUNDLE_ZIP to {BUNDLE_ZIP_NAME}. Running in dummy mode."
        )
    ensure_fp32_weights(_root)
    bundle = ModelBundle(_root)
except Exception as exc:  # keep the app up so /api/health can report the problem
    LOAD_ERROR = f"{exc}\n{traceback.format_exc()}"
    log.error("Model bundle failed to load:\n%s", LOAD_ERROR)

# ---------------------------------------------------------------------------
# Fallback dummy classes (used when the bundle is absent)
# ---------------------------------------------------------------------------
_DUMMY_CLASSES = [
    "Apple___Apple_scab", "Apple___Black_rot", "Apple___Cedar_apple_rust",
    "Apple___healthy", "Blueberry___healthy",
    "Cherry_(including_sour)___Powdery_mildew", "Cherry_(including_sour)___healthy",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
    "Corn_(maize)___Common_rust_", "Corn_(maize)___Northern_Leaf_Blight",
    "Corn_(maize)___healthy", "Grape___Black_rot", "Grape___Esca_(Black_Measles)",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)", "Grape___healthy",
    "Orange___Haunglongbing_(Citrus_greening)", "Peach___Bacterial_spot",
    "Peach___healthy", "Pepper,_bell___Bacterial_spot", "Pepper,_bell___healthy",
    "Potato___Early_blight", "Potato___Late_blight", "Potato___healthy",
    "Raspberry___healthy", "Soybean___healthy", "Squash___Powdery_mildew",
    "Strawberry___Leaf_scorch", "Strawberry___healthy", "Tomato___Bacterial_spot",
    "Tomato___Early_blight", "Tomato___Late_blight", "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite", "Tomato___Target_Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato___Tomato_mosaic_virus",
    "Tomato___healthy",
]

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="AI Crop Doctor API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()] if os.getenv("CORS_ORIGINS", "*") != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def dummy_predict(data: bytes) -> list[dict]:
    """Deterministic pseudo-random predictions used when the model is absent."""
    import hashlib
    seed = int.from_bytes(hashlib.sha256(data).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    classes = _DUMMY_CLASSES
    idx = rng.choice(len(classes), size=min(TOP_N, len(classes)), replace=False)
    top_conf = float(rng.uniform(0.40, 0.95))
    confs = [top_conf, (1 - top_conf) * 0.6, (1 - top_conf) * 0.3]
    return [
        {"class_id": int(i), "label": classes[int(i)], "confidence": round(float(c), 4)}
        for i, c in zip(idx, confs)
    ]


def decode_upload(data: bytes) -> Image.Image:
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"file too large (max {MAX_BYTES // (1024 * 1024)} MB)")
    try:
        image = Image.open(io.BytesIO(data))
        fmt = image.format
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="cannot read image")
    if fmt not in ("JPEG", "PNG", "WEBP"):
        raise HTTPException(status_code=415, detail="unsupported image type (JPEG, PNG or WebP only)")
    return image


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": bundle is not None,
        "num_classes": (sum(len(h["names"]) for h in bundle.disease_heads.values()) if bundle else len(_DUMMY_CLASSES)),
        "model_version": MODEL_VERSION if bundle is not None else "dummy-v0",
        "device": bundle.device if bundle else None,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "supported_crops": bundle.crop_names if bundle else [],
        "disease_heads": list(bundle.disease_heads) if bundle else [],
        "single_class_crops": sorted(bundle.single_class) if bundle else [],
        "min_crop_confidence": MIN_CROP_CONFIDENCE,
        "feature_mode": bundle.feature_mode if bundle else None,
        "error": LOAD_ERROR.splitlines()[0] if LOAD_ERROR else None,
    }


@app.post("/api/predict")
async def predict(file: UploadFile = File(...), known_crop: str | None = Form(default=None)):
    t0 = time.perf_counter()

    image = decode_upload(await file.read())

    try:
        if bundle is not None:
            result = bundle.classify(image, known_crop)
            predictions = [
                {"class_id": p["index"], "label": p["label"], "confidence": p["confidence"]}
                for p in result["predictions"]
            ]
            uncertain = result["uncertain"]
            predicted_crop = result["predicted_crop"]
            crop_confidence = result["crop_confidence"]
            routed_crop = result["routed_crop"]
            status = result["status"]
            note = result["note"]
            preprocess = result["preprocess"]
        else:
            predictions = dummy_predict(image.tobytes())
            uncertain = predictions[0]["confidence"] < CONFIDENCE_THRESHOLD
            predicted_crop = crop_confidence = routed_crop = note = preprocess = None
            status = "dummy"
    except Exception as exc:
        log.exception("inference failed")
        raise HTTPException(status_code=500, detail=f"inference error: {exc}")

    latency_ms = round((time.perf_counter() - t0) * 1000)

    return {
        "request_id": str(uuid.uuid4()),
        "model_version": MODEL_VERSION if bundle is not None else "dummy-v0",
        "latency_ms": latency_ms,
        "uncertain": uncertain,
        "predictions": predictions,
        "predicted_crop": predicted_crop,
        "crop_confidence": crop_confidence,
        "routed_crop": routed_crop,
        "status": status,
        "note": note,
        "preprocess": preprocess,   # every step between the upload and the model input
        "gradcam": None,          # this bundle does not produce Grad-CAM
    }


@app.post("/api/feedback")
def feedback(item: "FeedbackPayload"):
    # Accept any payload – log it and return ok.
    # Extend this to write to a DB / file when needed.
    print(f"[feedback] {item.model_dump()}")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Feedback schema
# ---------------------------------------------------------------------------
class FeedbackPayload(BaseModel):
    request_id: Optional[str] = None
    predicted_label: Optional[str] = None
    predicted_confidence: Optional[float] = None
    is_correct: Optional[bool] = None
    correct_label: Optional[str] = None
    lang: Optional[str] = None


# ---------------------------------------------------------------------------
# Serve the static frontend AFTER all /api routes
# ---------------------------------------------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    print(f"⚠️  Frontend directory not found: {FRONTEND_DIR}")
    print("   The API will work but the web UI will not be served.")
    print("   Copy the 'frontend/' folder next to main.py to fix this.")
