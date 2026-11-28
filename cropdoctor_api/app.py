"""AI Crop Doctor inference API. Same /api/predict contract as azure/main.py.
Model = final-omar v7, balanced_sampling variant (features: CLIP-L/336 embedding,
DINOv2-L (LoRA r8) CLS + mean patch, SigLIP so400m-384; router + per-crop heads)."""
import io, json, math, os, time, uuid, logging
from pathlib import Path
import numpy as np, torch
from torch import nn
from torch.nn import functional as F
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModel, CLIPVisionModel, SiglipVisionModel
from safetensors import safe_open
from huggingface_hub import snapshot_download, hf_hub_download

log = logging.getLogger("cropdoctor")
logging.basicConfig(level=logging.INFO)
WEIGHTS_REPO = os.environ.get("WEIGHTS_REPO", "omarwalied/ai-crop-doctor-weights")
HF_TOKEN = os.environ.get("HF_TOKEN")
WEIGHTS_DIR = os.environ.get("WEIGHTS_DIR", "")      # local folder override (tests)
CONF_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "0.60"))
MIN_CROP_CONF = float(os.environ.get("MIN_CROP_CONFIDENCE", "0.50"))
MODEL_VERSION = "final-omar-v7-balanced_sampling"
CLIP_NAME = "openai/clip-vit-large-patch14-336"; DINO_NAME = "facebook/dinov2-large"; SIG_NAME = "google/siglip-so400m-patch14-384"
CLIP_MEAN = [0.48145466, 0.4578275, 0.40821073]; CLIP_STD = [0.26862954, 0.26130258, 0.27577711]
DINO_MEAN = [0.485, 0.456, 0.406]; DINO_STD = [0.229, 0.224, 0.225]
MAX_BYTES = 10 * 1024 * 1024
torch.set_num_threads(max(1, os.cpu_count() or 1))

class LoRALinear(nn.Module):
    def __init__(self, base, r, alpha):
        super().__init__(); self.base = base; self.scale = alpha / r
        self.A = nn.Parameter(torch.zeros(r, base.in_features)); self.B = nn.Parameter(torch.zeros(base.out_features, r))
    def forward(self, x): return self.base(x) + (x @ self.A.t().to(x.dtype)) @ self.B.t().to(x.dtype) * self.scale

def inject_lora(m, r=8, alpha=16):
    n = 0
    for layer in m.encoder.layer:
        for nm, mod in list(layer.named_modules()):
            last = nm.split(".")[-1]
            if isinstance(mod, nn.Linear) and last in ("query", "value") and "attention" in nm:
                parent = layer; parts = nm.split(".")
                for p in parts[:-1]: parent = getattr(parent, p)
                setattr(parent, parts[-1], LoRALinear(mod, r, alpha)); n += 1
    assert n == len(m.encoder.layer) * 2, n
    return m

def make_head(d, k, cfg):
    return nn.Sequential(nn.Dropout(cfg["in_drop"]), nn.Linear(d, cfg["hidden"]), nn.GELU(), nn.Dropout(cfg["drop2"]), nn.Linear(cfg["hidden"], k))

def load_ck(path, names):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    cfg = ck.get("cfg") or dict(in_drop=.2, hidden=1024, drop2=.3)
    h = make_head(int(ck["D"]), int(ck["K"]), cfg); h.load_state_dict(ck["state"]); h.eval()
    assert len(names) == int(ck["K"]), (path, len(names), ck["K"])
    return dict(model=h, mu=ck["mu"].float(), sd=ck["sd"].float(), names=list(names))

class Bundle:
    def __init__(self, wdir: Path):
        self.wdir = wdir
        self.cfg = json.loads((wdir / "config.json").read_text())
        self.class_lists = json.loads((wdir / "class_lists.json").read_text())
        dt = torch.float32
        log.info("loading CLIP"); self.clip = CLIPVisionModel.from_pretrained(CLIP_NAME, torch_dtype=dt).eval()
        with safe_open(hf_hub_download(CLIP_NAME, "model.safetensors"), framework="pt") as f:
            self.proj = f.get_tensor("visual_projection.weight").float()
        log.info("loading DINOv2"); self.dino = inject_lora(AutoModel.from_pretrained(DINO_NAME, torch_dtype=dt).eval())
        sd = torch.load(wdir / "dinov2_lora_state.pt", map_location="cpu")
        if isinstance(sd, dict) and "state" in sd: sd = sd["state"]
        res = self.dino.load_state_dict(sd, strict=False)
        lora_loaded = [k for k in sd if k.endswith(".A") or k.endswith(".B")]
        missing_lora = [k for k in res.missing_keys if k.endswith(".A") or k.endswith(".B")]
        log.info("LoRA keys in file %d, missing LoRA keys %d, unexpected %d", len(lora_loaded), len(missing_lora), len(res.unexpected_keys))
        assert len(lora_loaded) == 48 and not missing_lora, (len(lora_loaded), missing_lora[:3], res.unexpected_keys[:3])
        for p in self.dino.parameters(): p.requires_grad_(False)
        log.info("loading SigLIP"); self.sig = SiglipVisionModel.from_pretrained(SIG_NAME, torch_dtype=dt).eval()
        self.router = load_ck(wdir / "router.pt", self.class_lists["router"])
        self.heads = {}
        for crop, fn in self.cfg["heads"].items():
            self.heads[crop] = load_ck(wdir / "heads" / fn, self.class_lists["diseases"][crop])
        self.crops = self.router["names"]
        log.info("ready crops=%s heads=%s", self.crops, list(self.heads))

    @staticmethod
    def _t(img, size, mean, std):
        a = np.asarray(img.resize((size, size), Image.Resampling.BICUBIC)).copy()
        x = torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).float() / 255
        return (x - torch.tensor(mean).view(1, 3, 1, 1)) / torch.tensor(std).view(1, 3, 1, 1)

    @torch.inference_mode()
    def features(self, image):
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        xc = self._t(rgb, 336, CLIP_MEAN, CLIP_STD); xd = self._t(rgb, 224, DINO_MEAN, DINO_STD); xs = self._t(rgb, 384, [.5] * 3, [.5] * 3)
        views = []
        for fl in (False, True):
            f = (lambda t: torch.flip(t, [3])) if fl else (lambda t: t)
            c = F.normalize(F.linear(self.clip(pixel_values=f(xc)).pooler_output, self.proj), dim=-1)
            t = self.dino(pixel_values=f(xd)).last_hidden_state; d = torch.cat([t[:, 0], t[:, 1:].mean(1)], -1)
            s = F.normalize(self.sig(pixel_values=f(xs)).pooler_output, dim=-1)
            views.append(torch.cat([c, d, s], -1))
        return torch.stack(views, 1)   # (1, 2, 3968)

    @torch.inference_mode()
    def run(self, ck, feat, n=3):
        x = (feat - ck["mu"]) / ck["sd"]
        pr = torch.softmax(ck["model"](x).mean(1), -1)[0].numpy()
        o = np.argsort(-pr)[:n]
        return [dict(index=int(i), label=ck["names"][int(i)], confidence=round(float(pr[int(i)]), 4)) for i in o]

    def classify(self, image, known_crop=None):
        feat = self.features(image)
        crop_top = self.run(self.router, feat); pc = crop_top[0]["label"]; cc = crop_top[0]["confidence"]
        routed = known_crop if known_crop in self.heads else pc
        if known_crop is None and cc < MIN_CROP_CONF:
            status, note, preds = "low_crop_confidence", "crop_not_confident_no_diagnosis", [dict(index=-1, label=f"{routed}___Unknown", confidence=0.0)]
        elif routed in self.heads:
            status, note, preds = "ok", None, self.run(self.heads[routed], feat)
        else:
            status, note, preds = "unsupported_crop", "no_trained_disease_head_for_crop", [dict(index=-1, label=f"{routed}___Unknown", confidence=0.0)]
        return dict(predicted_crop=pc, crop_confidence=cc, routed_crop=routed, predictions=preds, status=status, note=note,
                    uncertain=status != "ok" or preds[0]["confidence"] < CONF_THRESHOLD)

bundle = None; LOAD_ERROR = None
app = FastAPI(title="AI Crop Doctor API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _load():
    global bundle, LOAD_ERROR
    try:
        wdir = Path(WEIGHTS_DIR) if WEIGHTS_DIR else Path(snapshot_download(WEIGHTS_REPO, token=HF_TOKEN, cache_dir="/tmp/hfw"))
        bundle = Bundle(wdir)
    except Exception as e:
        import traceback; LOAD_ERROR = traceback.format_exc(); log.error(LOAD_ERROR)

@app.get("/api/health")
def health():
    return dict(status="ok" if bundle else "loading_or_failed", model_loaded=bundle is not None, model_version=MODEL_VERSION,
                supported_crops=bundle.crops if bundle else [], disease_heads=list(bundle.heads) if bundle else [],
                num_classes=sum(len(h["names"]) for h in bundle.heads.values()) if bundle else 0,
                confidence_threshold=CONF_THRESHOLD, device="cpu", error=(LOAD_ERROR or "").strip().splitlines()[-1] if LOAD_ERROR else None)

@app.post("/api/predict")
async def predict(file: UploadFile = File(...), known_crop: str | None = Form(default=None)):
    data = await file.read()
    if not data: raise HTTPException(422, "empty file")
    if len(data) > MAX_BYTES: raise HTTPException(413, "file too large (max 10 MB)")
    if bundle is None: raise HTTPException(503, "model not loaded: " + ((LOAD_ERROR or "still loading").strip().splitlines()[-1]))
    try:
        img = Image.open(io.BytesIO(data)); fmt = img.format; img.load()
    except (UnidentifiedImageError, OSError): raise HTTPException(422, "cannot read image")
    if fmt not in ("JPEG", "PNG", "WEBP"): raise HTTPException(415, "unsupported image type")
    t0 = time.perf_counter(); r = bundle.classify(img, known_crop)
    return dict(request_id=str(uuid.uuid4()), model_version=MODEL_VERSION, latency_ms=round((time.perf_counter() - t0) * 1000),
                uncertain=r["uncertain"], predictions=[dict(class_id=p["index"], label=p["label"], confidence=p["confidence"]) for p in r["predictions"]],
                predicted_crop=r["predicted_crop"], crop_confidence=r["crop_confidence"], routed_crop=r["routed_crop"],
                status=r["status"], note=r["note"], preprocess=None, gradcam=None)
