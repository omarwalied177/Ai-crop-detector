"""AI Crop Doctor - Streamlit front end (draft 2).
Look and strings come from web/ (css/styles.css palette, js/i18n.js EN/AR text).
Predictions: FastAPI service (azure/main.py) when API_URL is set, else a labelled demo mode.
Grad-CAM: not produced by the current model bundle, so a labelled placeholder is shown."""
import os, re, json, hashlib, pathlib
import streamlit as st

HERE = pathlib.Path(__file__).parent
API_URL = os.environ.get("API_URL", "").rstrip("/")
THRESHOLD = 0.60
st.set_page_config(page_title="AI Crop Doctor", page_icon="🌿", layout="centered")

@st.cache_data
def load_i18n():
    src = (HERE / "i18n.js").read_text(encoding="utf-8")
    a = src.index("ar: {")
    out = {}
    for lang, block in (("en", src[:a]), ("ar", src[a:])):
        out[lang] = dict(re.findall(r'\b(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', block))
    return out
T = load_i18n()

# Crops the Stage 2/3 model diagnoses vs only recognizes (from the project deck, page 4).
DIAGNOSED = {
    "Grape": ["Black rot", "Healthy"],
    "Corn": ["Gray leaf spot", "Common rust"],
    "Apple": ["Apple scab", "Healthy"],
    "Potato": ["Early blight", "Late blight"],
    "Tomato": ["Early blight", "Late blight", "Healthy"],
}
RECOGNIZED = ["Blueberry", "Cherry", "Peach", "Raspberry", "Soybean", "Squash", "Strawberry"]
LABELS = ["Tomato - Early blight", "Corn - Common rust", "Potato - Late blight", "Apple - Healthy"]

top = st.columns([6, 2, 2])
ar = top[1].toggle("العربية", value=False)
dark = top[2].toggle("🌙", value=False)
L = T["ar" if ar else "en"]
def t(k, **kw):
    v = L.get(k) or T["en"].get(k, k)
    return v.replace("{mb}", str(kw.get("mb", 10)))

V = dict(paper="#0c1812", surface="#132a1e", ink="#ecfdf5", muted="#86efac", line="#22523b", tint="#1c3e2d") if dark else \
    dict(paper="#f4f8f5", surface="#ffffff", ink="#064e3b", muted="#4b6b5b", line="#bbf7d0", tint="#ecfdf5")
direction = "rtl" if ar else "ltr"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Readex+Pro:wght@400;500;600;700&display=swap');
:root{{--paper:{V['paper']};--surface:{V['surface']};--ink:{V['ink']};--muted:{V['muted']};--line:{V['line']};--tint:{V['tint']};--leaf:#16a34a;--leaf-deep:#15803d;}}
html,body,.stApp,[class*="css"],p,span,div,label{{font-family:"IBM Plex Sans Arabic","IBM Plex Sans",system-ui,sans-serif;}}
.stApp{{background:var(--paper);color:var(--ink);}}
.block-container{{max-width:920px;padding-top:1rem !important;padding-bottom:3rem;direction:{direction};}}
#MainMenu,footer,header[data-testid="stHeader"]{{visibility:hidden;height:0;}}
.stMarkdown,.stMarkdown p,label,[data-testid="stToggle"] p{{color:var(--ink);}}
.brandrow{{display:flex;align-items:center;gap:12px;border-bottom:1px solid var(--line);padding:6px 0 14px;margin-bottom:22px}}
.logo{{width:32px;height:32px;border-radius:8px;background:var(--leaf-deep);display:grid;place-items:center;color:#fff;font-size:1.1rem}}
.brand-name{{font-family:"Readex Pro",sans-serif;font-weight:700;font-size:1.25rem;color:var(--ink)}}
.brand-badge{{background:var(--tint);border:1px solid var(--line);color:var(--leaf-deep);font-weight:600;font-size:.72rem;padding:4px 10px;border-radius:999px}}
h1.hero{{font-family:"Readex Pro","IBM Plex Sans Arabic",sans-serif;font-weight:700;font-size:2.5rem;line-height:1.2;color:var(--ink);margin:8px 0 14px}}
p.lede{{font-size:1.05rem;line-height:1.7;color:var(--muted);max-width:640px}}
.pills{{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 26px}}
.pill{{background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:7px 14px;font-weight:600;font-size:.85rem;color:var(--ink)}}
.steps{{display:inline-flex;gap:26px;background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:8px 14px;margin-bottom:18px}}
.step{{display:flex;align-items:center;gap:8px;font-weight:600;font-size:.9rem;color:var(--muted)}}
.dot{{width:28px;height:28px;border-radius:50%;border:1.5px solid var(--line);display:grid;place-items:center;font-size:.8rem}}
.step.cur{{color:var(--ink)}} .step.cur .dot{{background:var(--leaf);border-color:var(--leaf);color:#fff}}
.dz-top{{text-align:center;margin-top:6px}}
.dz-icon{{width:68px;height:68px;border-radius:50%;background:var(--tint);display:grid;place-items:center;margin:0 auto 6px;font-size:1.9rem}}
.dz-title{{font-family:"Readex Pro","IBM Plex Sans Arabic",sans-serif;font-weight:700;font-size:1.35rem;color:var(--ink);margin:0}}
.dz-hint{{text-align:center;color:var(--muted);font-size:.85rem;margin:6px 0 10px}}
[data-testid="stFileUploaderDropzone"]{{align-items:center !important;justify-content:center !important;background:var(--surface);border:2px dashed var(--line);border-radius:18px;padding:22px;flex-direction:column;justify-content:center;gap:6px}}
[data-testid="stFileUploaderDropzoneInstructions"]{{display:none}}
[data-testid="stFileUploaderDropzone"] button{{font-size:0;background:linear-gradient(135deg,#16a34a,#15803d);border:none;border-radius:12px;padding:.8rem 2rem;box-shadow:0 4px 14px rgba(21,128,61,.3)}}
[data-testid="stFileUploaderDropzone"] button *{{display:none}}
[data-testid="stFileUploaderDropzone"] button::after{{content:"{t('btn_choose')}";font-size:1.05rem;font-weight:700;color:#fff}}
.stButton>button{{background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;border:none;border-radius:12px;font-weight:700}}
.card{{background:var(--surface);border:1.5px solid var(--line);border-radius:18px;padding:16px 20px;box-shadow:0 4px 16px rgba(6,78,59,.08)}}
h3.sec{{font-family:"Readex Pro","IBM Plex Sans Arabic",sans-serif;font-weight:700;color:var(--ink);margin:30px 0 12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
.tip,.how{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:14px 16px;font-size:.88rem;color:var(--muted)}}
.tip b,.how b{{display:block;color:var(--ink);font-size:.95rem;margin-bottom:3px}}
.num{{width:30px;height:30px;border-radius:50%;border:2px solid var(--leaf);display:grid;place-items:center;font-weight:700;color:var(--leaf);margin-bottom:8px}}
.res-title{{font-family:"Readex Pro",sans-serif;font-weight:700;font-size:1.5rem;color:var(--ink)}}
.bar{{height:10px;background:var(--tint);border-radius:999px;overflow:hidden;margin:4px 0 12px}}
.bar>div{{height:100%;background:linear-gradient(90deg,#22c55e,#15803d)}}
.warn,.demo{{background:#fef3c7;border:1.5px solid #f59e0b;color:#78350f;border-radius:12px;padding:10px 14px;font-weight:600;font-size:.88rem;margin-bottom:10px}}
.cls{{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}}
.chip{{background:var(--tint);border:1px solid var(--line);border-radius:999px;padding:3px 10px;font-size:.8rem;color:var(--ink)}}
.chip.muted{{opacity:.7}}
.gc{{border:1.5px dashed var(--line);border-radius:12px;padding:12px;color:var(--muted);font-size:.85rem;margin-top:10px}}
</style>
""", unsafe_allow_html=True)

st.markdown(f'<div class="brandrow"><span class="logo">🌿</span><span class="brand-name">{t("app_name")}</span>'
            f'<span class="brand-badge">{t("hero_badge")}</span></div>'
            f'<h1 class="hero">{t("hero_title")}</h1><p class="lede">{t("hero_sub")}</p>'
            f'<div class="pills"><span class="pill">🌿 {"١٢ محصولًا" if ar else "12 crops"}</span><span class="pill">⚡ Instant AI Analysis</span>'
            '<span class="pill">🔬 Explainable (Grad-CAM planned)</span><span class="pill">🌍 English &amp; العربية</span></div>',
            unsafe_allow_html=True)

def predict(data: bytes, name: str):
    if API_URL:
        import requests
        r = requests.post(f"{API_URL}/api/predict", files={"file": (name, data)}, timeout=30)
        r.raise_for_status(); raw = r.json()
        preds = raw.get("predictions") or raw.get("top3") or raw.get("results")
        return [(p.get("label"), float(p.get("confidence", 0))) for p in preds[:3]], False
    h = int(hashlib.sha256(data).hexdigest(), 16)
    a = LABELS[h % 4]; rest = [l for l in LABELS if l != a]
    return [], True

steps_ph = st.empty()
st.markdown(f'<div class="dz-top"><div class="dz-icon">🍃</div><p class="dz-title">{t("dz_title")}</p></div>'
            f'<p class="dz-hint">{t("dz_hint", mb=10)}</p>', unsafe_allow_html=True)
photo = st.file_uploader("photo", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
cur = 3 if (photo or st.session_state.get("sample")) else 1
steps = "".join(f'<span class="step {"cur" if i == cur else ""}"><span class="dot">{i}</span>{t(k)}</span>'
                for i, k in [(1, "step_photo"), (2, "step_analyse"), (3, "step_result")])
steps_ph.markdown(f'<div class="steps">{steps}</div>', unsafe_allow_html=True)

SAMPLES = json.loads((HERE / "samples" / "samples.json").read_text()) if (HERE / "samples" / "samples.json").exists() else {}
st.markdown('<div class="card"><b>🍃 Sample photos (real PlantVillage lab photos, true label shown). Click one to test:</b></div>', unsafe_allow_html=True)
chosen = None
cols = st.columns(4)
for i, (k, m) in enumerate(SAMPLES.items()):
    name = m["label"].replace("___", " - ").replace("_", " ").replace("(maize)", "").replace("  ", " ").strip()
    if cols[i % 4].button(name, key="s_" + k, use_container_width=True):
        st.session_state["sample"] = k
if photo:
    st.session_state.pop("sample", None)
elif st.session_state.get("sample") in SAMPLES:
    chosen = st.session_state["sample"]

if photo or chosen:
    data = photo.getvalue() if photo else (HERE / "samples" / f"{chosen}.jpg").read_bytes()
    if chosen:
        st.caption("Sample: true label = " + SAMPLES[chosen]["label"] + ". Source: " + SAMPLES[chosen]["source"])
    c1, c2 = st.columns(2)
    c1.image(data, use_container_width=True)
    preds, demo = predict(data, photo.name if photo else chosen + ".jpg")
    with c2:
        if demo:
            st.markdown('<div class="demo">No model is connected to this draft, so no diagnosis is shown. Set API_URL to the FastAPI service to get real predictions.</div>', unsafe_allow_html=True)
            st.markdown('<div class="card"><div class="gc" style="margin:0">Grad-CAM: not available for the current model (frozen CLIP + DINOv2 features, no CNN gradient path). No heatmap is being faked.</div></div>', unsafe_allow_html=True)
        else:
            if preds[0][1] < THRESHOLD:
                st.markdown('<div class="warn">Not sure. Retake the photo: one leaf, natural light, plain background.</div>', unsafe_allow_html=True)
            html = f'<div class="card"><div class="res-title">{preds[0][0]}</div>'
            for l, c in preds:
                html += f'<div style="display:flex;justify-content:space-between;font-weight:600"><span>{l}</span><span>{c*100:.0f}%</span></div><div class="bar"><div style="width:{c*100:.0f}%"></div></div>'
            html += '<div class="gc">Grad-CAM: not available for the current model (frozen CLIP + DINOv2 features, no CNN gradient path). No heatmap is being faked.</div></div>'
            st.markdown(html, unsafe_allow_html=True)

st.markdown(f'<h3 class="sec">{t("tips_title")}</h3><div class="grid">'
            + "".join(f'<div class="tip"><b>{t(a)}</b>{t(b)}</div>' for a, b in
                      [("tip_single_title", "tip_1"), ("tip_light_title", "tip_2"), ("tip_focus_title", "tip_3"), ("tip_bg_title", "tip_4")])
            + '</div>', unsafe_allow_html=True)
st.markdown(f'<h3 class="sec">{t("how_title")}</h3><div class="grid">'
            + "".join(f'<div class="how"><div class="num">{i}</div><b>{t(a)}</b>{t(b)}</div>' for i, (a, b) in
                      enumerate([("how_1_t", "how_1_d"), ("how_2_t", "how_2_d"), ("how_3_t", "how_3_d")], 1))
            + '</div>', unsafe_allow_html=True)

chips = "".join(f'<div style="margin-top:10px"><b>{c}</b><div class="cls">' + "".join(f'<span class="chip">{d}</span>' for d in ds) + '</div></div>' for c, ds in DIAGNOSED.items())
rec = "".join(f'<span class="chip muted">{c}</span>' for c in RECOGNIZED)
st.markdown('<h3 class="sec">Supported classes</h3><div class="card">The model diagnoses these conditions per crop:'
            f'{chips}<div style="margin-top:14px"><b>Crop recognized, no diagnosis yet</b><div class="cls">{rec}</div></div>'
            '<p style="color:var(--muted);font-size:.8rem;margin-top:12px">Source: project results deck (Stage 2). Tomato may use a larger head in the API. To be confirmed against the final run.</p></div>', unsafe_allow_html=True)
