/* AI Crop Doctor - front-end application logic. No framework, no build step. */
(function () {
  "use strict";

  var DEFAULTS = { API_BASE: "", PREDICT_PATH: "/api/predict", FEEDBACK_PATH: "/api/feedback", MOCK: false, MAX_UPLOAD_MB: 10,
    ACCEPTED_TYPES: ["image/jpeg", "image/png", "image/webp"], CONFIDENCE_THRESHOLD: 0.70, REQUEST_TIMEOUT_MS: 30000,
    FEEDBACK_ENABLED: true, DEFAULT_LANG: "auto" };
  var CFG = Object.assign({}, DEFAULTS, window.APP_CONFIG || {});
  try { if (new URLSearchParams(window.location.search).get("mock") === "1") CFG.MOCK = true; } catch (e) { /* ignore */ }

  var I = window.CD_I18N, t = I.t, API = window.CD_API;
  var KB = window.CD_KB || { crops: {}, conditions: {}, types: {} };

  var $ = function (id) { return document.getElementById(id); };
  var noop = function () {};
  var VIEWS = ["input", "preview", "loading", "error", "result"];
  var EXT_OK = /\.(jpe?g|png|webp)$/i;

  var state = {
    view: "input", file: null, previewUrl: null, resized: false, quality: [],
    result: null, selected: 0, kbOpen: true, vizMode: "cam", opacity: 0.6, heatSrc: null,
    abort: null, error: null, loadTimer: null, loadIdx: 0,
    fb: { done: false, wrong: false, busy: false, status: null },
    camStream: null, camFacing: "environment"
  };

  /* ---------- helpers ---------- */
  function el(tag, props, kids) {
    var n = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      var v = props[k];
      if (v === null || v === undefined || v === false) return;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v === true ? "" : String(v));
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  function norm(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, ""); }
  var kbIndex = {};
  Object.keys(KB.conditions || {}).forEach(function (k) { kbIndex[norm(k)] = k; });

  function isoNum(s) { return I.getLang() === "ar" ? "\u2066" + s + "\u2069" : s; }   /* keep numbers intact inside Arabic text */
  function pct(c) { return (c * 100).toFixed(1) + "%"; }

  function displayName(label) {
    var lang = I.getLang(), key = kbIndex[norm(label)], e = key ? KB.conditions[key] : null;
    if (e) {
      var crop = (KB.crops[e.crop] && KB.crops[e.crop][lang]) || e.crop;
      return { crop: crop, condition: e.name[lang] || e.name.en, type: e.type, entry: e, key: key };
    }
    var parts = String(label).split("___");
    return { crop: parts[0].replace(/_/g, " ").trim(), condition: (parts[1] || parts[0]).replace(/_/g, " ").trim(), type: null, entry: null, key: null };
  }
  function fullName(d) { return d.crop && d.crop !== d.condition ? d.crop + ": " + d.condition : d.condition; }

  function icon(name) {
    var paths = {
      ok: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
      warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4m0 3v.01"/>',
      info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8v.01"/>'
    };
    var s = document.createElement("span");
    s.setAttribute("aria-hidden", "true");
    s.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">' + (paths[name] || paths.info) + "</svg>";
    return s;
  }

  /* ---------- views ---------- */
  function showView(name, focusEl, step) {
    state.view = name;
    VIEWS.forEach(function (v) { $(v + "View").hidden = (v !== name); });
    var cur = step || (name === "loading" ? 2 : name === "result" ? 3 : 1);
    Array.prototype.forEach.call($("steps").children, function (li) {
      var n = Number(li.getAttribute("data-step"));
      li.classList.toggle("is-current", n === cur);
      li.classList.toggle("is-done", n < cur);
      if (n === cur) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
    });

    var btnH = $("btnNewHeader");
    if (btnH) btnH.hidden = (name !== "result" && name !== "preview");
    var sticky = $("resultStickyBar");
    if (sticky && name !== "result") sticky.hidden = true;

    if (name !== "input") {
      try { $("diagnose").scrollIntoView({ block: "start", behavior: "smooth" }); } catch (e) { /* ignore */ }
    }
    if (focusEl) {
      try { focusEl.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
    }
  }

  /* ---------- file handling ---------- */
  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var u = URL.createObjectURL(file), im = new Image(), done = false;
      var finish = function (fn, v) { if (done) return; done = true; clearTimeout(timer); URL.revokeObjectURL(u); fn(v); };
      var timer = setTimeout(function () { finish(reject, new Error("decode timeout")); }, 15000);
      im.onload = function () { finish(resolve, im); };
      im.onerror = function () { finish(reject, new Error("decode")); };
      im.src = u;
    });
  }
  function shrink(file, maxSide, quality) {
    return loadImage(file).then(function (img) {
      var s = Math.min(1, maxSide / Math.max(img.naturalWidth, img.naturalHeight));
      var c = document.createElement("canvas");
      c.width = Math.max(1, Math.round(img.naturalWidth * s)); c.height = Math.max(1, Math.round(img.naturalHeight * s));
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      return new Promise(function (resolve) {
        c.toBlob(function (b) {
          resolve(b ? new File([b], (file.name || "photo").replace(/\.[^.]+$/, "") + ".jpg", { type: "image/jpeg" }) : null);
        }, "image/jpeg", quality);
      });
    }).catch(function () { return null; });
  }

  function handleFile(file) {
    if (!file) return Promise.resolve();
    var okType = CFG.ACCEPTED_TYPES.indexOf(file.type) !== -1 || (!file.type && EXT_OK.test(file.name || ""));
    if (!okType) return Promise.resolve(showError("err_type", { step: 1 }));
    if (!file.size) return Promise.resolve(showError("err_decode", { step: 1 }));
    var maxBytes = CFG.MAX_UPLOAD_MB * 1024 * 1024;
    if (file.size <= maxBytes) { setFile(file, false); return Promise.resolve(); }
    return shrink(file, 2560, 0.88).then(function (small) {
      if (!small || small.size > maxBytes) showError("err_size", { step: 1, vars: { mb: CFG.MAX_UPLOAD_MB } });
      else setFile(small, true);
    });
  }

  function revokePreview() { if (state.previewUrl) { try { URL.revokeObjectURL(state.previewUrl); } catch (e) { /* ignore */ } } state.previewUrl = null; }

  function setFile(file, resized) {
    revokePreview();
    state.file = file; state.resized = resized; state.quality = []; state.result = null;
    state.previewUrl = URL.createObjectURL(file);
    var img = $("previewImg");
    img.onload = function () { analyseQuality(img); };
    img.onerror = function () { showError("err_decode", { step: 1 }); };
    img.alt = t("preview_alt");
    img.src = state.previewUrl;
    $("fileInfo").textContent = (file.name || "photo") + "  (" + (file.size / 1048576).toFixed(1) + " MB)";
    renderHints();
    showView("preview", $("btnAnalyse"));
  }

  function analyseQuality(img) {
    var hints = [], w = img.naturalWidth, h = img.naturalHeight;
    if (Math.min(w, h) < 224) hints.push(["hint_small", { w: w, h: h }]);
    try {
      var s = Math.min(1, 256 / Math.max(w, h)), cw = Math.max(8, Math.round(w * s)), ch = Math.max(8, Math.round(h * s));
      var c = document.createElement("canvas"); c.width = cw; c.height = ch;
      var ctx = c.getContext("2d", { willReadFrequently: true });
      if (ctx) {
        ctx.drawImage(img, 0, 0, cw, ch);
        var d = ctx.getImageData(0, 0, cw, ch).data, n = cw * ch, g = new Float32Array(n), sum = 0, i, j;
        for (i = 0, j = 0; i < n; i++, j += 4) { g[i] = 0.2126 * d[j] + 0.7152 * d[j + 1] + 0.0722 * d[j + 2]; sum += g[i]; }
        var mean = sum / n;
        if (mean < 50) hints.push(["hint_dark"]); else if (mean > 215) hints.push(["hint_bright"]);
        var a1 = 0, a2 = 0, cnt = 0, x, y, k, lap;
        for (y = 1; y < ch - 1; y++) for (x = 1; x < cw - 1; x++) {
          k = y * cw + x; lap = 4 * g[k] - g[k - 1] - g[k + 1] - g[k - cw] - g[k + cw]; a1 += lap; a2 += lap * lap; cnt++;
        }
        if (cnt && (a2 / cnt - (a1 / cnt) * (a1 / cnt)) < 12) hints.push(["hint_blur"]);
      }
    } catch (e) { /* quality hints are optional */ }
    state.quality = hints; renderHints();
  }

  function renderHints() {
    var ul = $("qualityHints"); ul.textContent = "";
    var all = state.quality.slice();
    if (state.resized) all.push(["hint_resized", { mb: CFG.MAX_UPLOAD_MB }]);
    all.forEach(function (h) { ul.appendChild(el("li", { text: t(h[0], h[1]) })); });
  }

  /* ---------- analysis ---------- */
  function startLoadingText() {
    state.loadIdx = 0; $("loadingStep").textContent = t("load_1");
    stopLoadingText();
    state.loadTimer = setInterval(function () {
      state.loadIdx = Math.min(state.loadIdx + 1, 2);
      $("loadingStep").textContent = t("load_" + (state.loadIdx + 1));
    }, 2500);
  }
  function stopLoadingText() { if (state.loadTimer) { clearInterval(state.loadTimer); state.loadTimer = null; } }

  function analyse() {
    if (!state.file) return;
    if (state.abort) state.abort.abort();
    var ctrl = new AbortController(); state.abort = ctrl;
    showView("loading", $("loadingStep"));
    startLoadingText();
    API.predict(state.file, CFG, { signal: ctrl.signal }).then(function (res) {
      if (state.abort !== ctrl) return;
      stopLoadingText(); state.abort = null;
      state.result = res; state.selected = 0; state.kbOpen = !res.uncertain; state.vizMode = "cam";
      state.heatSrc = null; state.fb = { done: false, wrong: false, busy: false, status: null };
      renderResult(); showView("result", $("resultHeading"));
      renderDemoBanner();
    }).catch(function (err) {
      if (state.abort !== ctrl) return;
      stopLoadingText(); state.abort = null;
      if (err && err.code === "aborted") { showView("preview", $("btnAnalyse")); return; }
      showError(errorKey(err), { step: 2, retry: analyse });
    });
  }

  function errorKey(e) {
    var map = { network: "err_network", timeout: "err_timeout", bad_response: "err_bad_response", server: "err_server",
      http_413: "err_413", http_415: "err_415", http_422: "err_422", http_429: "err_429" };
    return map[e && e.code] || "err_server";
  }

  function showError(key, opts) {
    opts = opts || {};
    state.error = { key: key, vars: opts.vars || null, step: opts.step || 1, retry: opts.retry || null };
    renderError();
    showView("error", $("errorTitle"), state.error.step);
  }
  function renderError() {
    if (!state.error) return;
    $("errorTitle").textContent = t("error_title");
    $("errorMsg").textContent = t(state.error.key, state.error.vars);
    $("btnRetry").hidden = !state.error.retry;
  }

  /* ---------- result rendering ---------- */
  function renderResult() {
    var r = state.result; if (!r) return;
    var d0 = displayName(r.predictions[0].label), p0 = pct(r.predictions[0].confidence);

    var card = $("statusCard"); card.textContent = "";
    card.className = "callout" + (r.uncertain ? " callout-warn" : "");
    var title, msg;
    if (r.uncertain) { title = t("res_unsure_title"); msg = t("res_unsure_msg", { pct: isoNum(p0) }); }
    else if (d0.type === "healthy") { title = t("res_healthy_title"); msg = t("res_healthy_msg", { name: fullName(d0), pct: isoNum(p0) }); }
    else { title = t("res_ok_title", { name: fullName(d0) }); msg = t("res_ok_msg", { pct: isoNum(p0) }); }
    card.appendChild(icon(r.uncertain ? "warn" : "ok"));
    card.appendChild(el("div", null, [el("h3", { id: "resultHeading", tabindex: "-1", text: title }), el("p", { text: msg })]));

    // Update sticky floating bar values
    var stickyName = $("stickyDiagnosisName"), stickyConf = $("stickyDiagnosisConf");
    if (stickyName) stickyName.textContent = fullName(d0);
    if (stickyConf) stickyConf.textContent = isoNum(p0) + (d0.type ? " • " + t("type_" + d0.type) : "");

    renderViz(); renderPredictions(); renderMeta(); renderPreprocess(); renderKB(); renderFeedback();
  }

  /* Preprocessing pipeline: the steps the backend applied to this exact photo. */
  function renderPreprocess() {
    var panel = $("prepPanel"), strip = $("prepStrip");
    if (!panel || !strip) return;
    var p = state.result && state.result.preprocess;
    panel.hidden = !p;
    strip.textContent = "";
    if (!p) return;
    p.steps.forEach(function (s, i) {
      var key = "prep_" + s.id + "_t", label = t(key);
      if (label === key) label = s.label || s.id;
      strip.appendChild(el("li", { "class": "prep-step" }, [
        s.preview ? el("img", { "class": "prep-img", src: s.preview, alt: t("prep_alt", { n: i + 1, step: label }), loading: "lazy" }) : null,
        el("div", { "class": "prep-txt" }, [
          el("strong", { text: label }),
          el("span", { "class": "fine", dir: "auto", text: s.detail })
        ])
      ]));
    });
  }

  function renderViz() {
    var r = state.result, g = r.gradcam || {}, base = $("vizBase"), heat = $("vizHeat");
    if (base.getAttribute("src") !== state.previewUrl) base.src = state.previewUrl;
    base.alt = t("gc_alt_photo");
    var hasCam = !!(g.overlay || g.heatmap), showCam = hasCam && state.vizMode === "cam";
    $("vizTools").hidden = !hasCam;
    $("gcCaption").textContent = hasCam ? t("gc_caption") : t("gc_none");
    if (!hasCam) { heat.hidden = true; base.hidden = false; return; }
    $("vizOriginal").setAttribute("aria-pressed", String(!showCam));
    $("vizGradcam").setAttribute("aria-pressed", String(showCam));
    var src = g.heatmap || g.overlay;
    if (state.heatSrc !== src) { heat.src = src; state.heatSrc = src; }
    heat.alt = showCam ? t("gc_alt_cam") : "";
    heat.hidden = !showCam;
    if (g.heatmap) {          /* transparent heat-map: blend over the photo with an adjustable strength */
      heat.style.opacity = String(state.opacity); base.hidden = false; $("opacityWrap").hidden = !showCam;
      $("opacity").value = String(Math.round(state.opacity * 100));
    } else {                  /* ready-made overlay image from the backend replaces the photo */
      heat.style.opacity = "1"; base.hidden = showCam; $("opacityWrap").hidden = true;
    }
  }

  function renderPredictions() {
    var list = $("predList"); list.textContent = "";
    state.result.predictions.forEach(function (p, i) {
      var d = displayName(p.label), p100 = pct(p.confidence), selected = state.kbOpen && state.selected === i;
      var btn = el("button", { type: "button", "class": "pred" + (d.type ? " t-" + d.type : ""), "data-i": i, "aria-pressed": String(selected) }, [
        el("span", { "class": "pred-top" }, [
          el("span", { "class": "pred-name" }, [el("span", { "class": "pred-crop", text: d.crop }), " ", d.condition]),
          el("span", { "class": "pred-pct", dir: "ltr", "aria-hidden": "true", text: p100 })
        ]),
        el("span", { "class": "sr-only", text: t("conf_aria", { pct: p100 }) }),
        el("span", { "class": "gauge", "aria-hidden": "true" }, [el("i", { style: "width:" + (p.confidence * 100).toFixed(1) + "%" })]),
        d.type ? el("span", { "class": "badge", text: t("type_" + d.type) }) : null
      ]);
      list.appendChild(el("li", null, [btn]));
    });
  }

  function renderMeta() {
    var r = state.result, m = $("metaLine"); m.textContent = "";
    var parts = [];
    if (r.modelVersion) parts.push(t("meta_model", { v: r.modelVersion }));
    if (r.latencyMs !== null) parts.push(t("meta_time", { ms: Math.round(r.latencyMs) }));
    m.textContent = parts.join("   ");
  }

  function list(items) { return el("ul", null, (items || []).map(function (x) { return el("li", { text: x }); })); }

  function renderKB() {
    var panel = $("kbPanel"); panel.textContent = "";
    if (!state.kbOpen) { panel.appendChild(el("p", { "class": "kb-hint", text: t("kb_pick") })); return; }
    var lang = I.getLang(), p = state.result.predictions[state.selected], d = displayName(p.label), e = d.entry;

    panel.appendChild(el("div", { "class": "kb-head" }, [el("h3", { text: d.condition }), el("span", { "class": "kb-crop", text: d.crop })]));
    if (!e) {
      panel.appendChild(el("p", { "class": "kb-empty kb-note", text: t("kb_none") }));
    } else {
      var type = KB.types[e.type] || {};
      if (e.notes && e.notes[lang]) {
        var note = el("div", { "class": "callout kb-note" }, [icon("info"), el("div", null, [el("strong", { text: t("kb_key") }), el("p", { text: e.notes[lang] })])]);
        panel.appendChild(note);
      }
      var cause = el("div", null, [el("p", { text: t("type_" + e.type) })]);
      if (e.pathogen) cause.appendChild(el("p", { "class": "kb-path" }, [t("kb_agent") + ": ", el("em", { text: e.pathogen })]));
      else cause.appendChild(el("p", { "class": "kb-path", text: t("cause_healthy") }));
      var mgmt = (e.management || type.management || {})[lang], prev = (e.prevention || type.prevention || {})[lang];
      function sec(titleKey, body) { return el("section", { "class": "kb-sec" }, [el("h4", { text: t(titleKey) }), body]); }
      panel.appendChild(el("div", { "class": "kb-grid" }, [
        sec("kb_symptoms", list(e.symptoms && e.symptoms[lang])), sec("kb_cause", cause),
        sec("kb_management", list(mgmt)), sec("kb_prevention", list(prev))
      ]));
      if (e.sources && e.sources.length) {
        var ul = el("ul");
        e.sources.forEach(function (s) {
          var title = (typeof s === "string") ? s : (s.title || s.url || ""), url = (s && typeof s === "object" && /^https?:\/\//i.test(s.url || "")) ? s.url : null;
          ul.appendChild(el("li", null, [url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: title }) : title]));
        });
        panel.appendChild(el("div", { "class": "kb-sources fine" }, [el("strong", { text: t("kb_sources") }), ul]));
      }
    }
    panel.appendChild(el("div", { "class": "callout callout-warn kb-disclaimer" }, [icon("info"), el("p", { text: t("disclaimer") })]));
  }

  /* ---------- feedback ---------- */
  function fillFeedbackOptions() {
    var sel = $("fbSelect"), prev = sel.value, lang = I.getLang();
    sel.textContent = "";
    sel.appendChild(el("option", { value: "", text: t("fb_choose") }));
    var rows = Object.keys(KB.conditions).map(function (k) { var d = displayName(k); return { k: k, text: fullName(d) }; });
    rows.sort(function (a, b) { return a.text.localeCompare(b.text, lang); });
    rows.forEach(function (r) { sel.appendChild(el("option", { value: r.k, text: r.text })); });
    sel.appendChild(el("option", { value: "__unknown__", text: t("fb_unknown") }));
    if (prev) sel.value = prev;
    $("fbSend").disabled = !sel.value;
  }
  function renderFeedback() {
    var panel = $("feedbackPanel");
    panel.hidden = !CFG.FEEDBACK_ENABLED;
    if (!CFG.FEEDBACK_ENABLED) return;
    fillFeedbackOptions();
    var fb = state.fb;
    $("fbChoice").hidden = fb.done || fb.wrong;
    $("fbWrong").hidden = fb.done || !fb.wrong;
    $("fbYes").disabled = $("fbNo").disabled = $("fbSend").disabled = fb.busy;
    if (!fb.wrong) $("fbSend").disabled = true;
    else $("fbSend").disabled = fb.busy || !$("fbSelect").value;
    var s = $("fbStatus"); s.className = "fb-status" + (fb.status ? " " + fb.status.cls : ""); s.textContent = fb.status ? t(fb.status.key) : "";
  }
  function submitFeedback(isCorrect, correctLabel) {
    var r = state.result, fb = state.fb; if (!r || fb.busy) return;
    fb.busy = true; fb.status = { key: "fb_sending", cls: "" }; renderFeedback();
    var payload = { request_id: r.requestId, predicted_label: r.predictions[0].label, predicted_confidence: r.predictions[0].confidence,
      is_correct: isCorrect, correct_label: correctLabel, lang: I.getLang() };
    API.sendFeedback(payload, CFG).then(function () {
      fb.busy = false; fb.done = true; fb.status = { key: "fb_thanks", cls: "ok" }; renderFeedback();
    }).catch(function () {
      fb.busy = false; fb.status = { key: "fb_error", cls: "bad" }; renderFeedback();
    });
  }

  /* ---------- camera ---------- */
  function coarsePointer() { try { return window.matchMedia("(pointer: coarse)").matches; } catch (e) { return false; } }
  function canUseCameraDialog() {
    var dlg = $("cameraDialog");
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.isSecureContext && dlg && typeof dlg.showModal === "function");
  }
  function onCapture() {
    if (coarsePointer() || !canUseCameraDialog()) { $("captureInput").click(); return; }   /* phones: native camera app */
    openCamera();
  }
  function stopStream() {
    if (state.camStream) { state.camStream.getTracks().forEach(function (tr) { tr.stop(); }); state.camStream = null; }
    var v = $("camVideo"); if (v) v.srcObject = null;
  }
  function startStream() {
    stopStream();
    return navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: state.camFacing }, width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false }).then(function (s) {
      state.camStream = s; var v = $("camVideo"); v.srcObject = s;
      return v.play().catch(noop);
    });
  }
  function cameraErrorKey(e) {
    var n = e && e.name;
    if (n === "NotAllowedError" || n === "SecurityError") return "err_cam_denied";
    if (n === "NotFoundError" || n === "OverconstrainedError" || n === "DevicesNotFoundError") return "err_cam_none";
    return "err_cam_generic";
  }
  function openCamera() {
    var dlg = $("cameraDialog");
    $("camMsg").textContent = t("cam_starting");
    if (!dlg.open) dlg.showModal();
    startStream().then(function () { $("camMsg").textContent = t("cam_ready"); }).catch(function (e) {
      if (dlg.open) dlg.close();
      showError(cameraErrorKey(e), { step: 1, retry: onCapture });
    });
  }
  function shoot() {
    var v = $("camVideo");
    if (!v.videoWidth) return;
    var c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    c.toBlob(function (b) {
      if (!b) return;
      var f = new File([b], "leaf-" + Date.now() + ".jpg", { type: "image/jpeg" });
      $("cameraDialog").close();
      handleFile(f);
    }, "image/jpeg", 0.92);
  }
  function switchCamera() {
    var prev = state.camFacing;
    state.camFacing = prev === "environment" ? "user" : "environment";
    startStream().catch(function () { state.camFacing = prev; startStream().catch(noop); });
  }

  /* ---------- sample leaf generation ---------- */
  function generateSampleLeaf(sampleType) {
    var canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Neutral soft backdrop
    ctx.fillStyle = "#edf2ec";
    ctx.fillRect(0, 0, 512, 512);

    ctx.save();
    ctx.translate(256, 256);
    ctx.rotate(-0.06);

    if (sampleType === "corn_rust") {
      // Corn leaf blade
      ctx.beginPath();
      ctx.moveTo(-110, 210);
      ctx.quadraticCurveTo(-90, -40, 0, -220);
      ctx.quadraticCurveTo(90, -40, 110, 210);
      ctx.closePath();
      var grad = ctx.createLinearGradient(0, -220, 0, 210);
      grad.addColorStop(0, "#4d9036");
      grad.addColorStop(0.5, "#5da43f");
      grad.addColorStop(1, "#3f7a2c");
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = "#2e5c1e";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Parallel veins
      ctx.strokeStyle = "rgba(255,255,255,0.25)";
      ctx.lineWidth = 1.4;
      for (var x = -80; x <= 80; x += 15) {
        ctx.beginPath();
        ctx.moveTo(x * 0.9, 200);
        ctx.quadraticCurveTo(x * 0.6, 0, x * 0.1, -200);
        ctx.stroke();
      }

      // Rust pustules
      var pustules = [
        [-30, -100], [-15, -80], [-35, -60], [10, -70], [20, -50],
        [-12, -30], [28, -20], [-25, 15], [12, 25], [-8, 50],
        [32, 60], [-20, 90], [15, 105], [0, 130], [-25, 150]
      ];
      pustules.forEach(function (pt) {
        ctx.save();
        ctx.translate(pt[0], pt[1]);
        ctx.beginPath();
        ctx.ellipse(0, 0, 9, 5, 0.2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(202, 138, 4, 0.4)";
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(0, 0, 6, 3, 0.2, 0, Math.PI * 2);
        ctx.fillStyle = "#b45309";
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(0, 0, 4, 1.8, 0.2, 0, Math.PI * 2);
        ctx.fillStyle = "#78350f";
        ctx.fill();
        ctx.restore();
      });

    } else if (sampleType === "potato_late_blight") {
      // Broad potato leaflet
      ctx.beginPath();
      ctx.moveTo(0, 200);
      ctx.bezierCurveTo(-160, 130, -170, -70, 0, -210);
      ctx.bezierCurveTo(170, -70, 160, 130, 0, 200);
      ctx.closePath();
      var pGrad = ctx.createLinearGradient(-130, 0, 130, 0);
      pGrad.addColorStop(0, "#3e7b30");
      pGrad.addColorStop(0.5, "#4d963c");
      pGrad.addColorStop(1, "#366d29");
      ctx.fillStyle = pGrad;
      ctx.fill();
      ctx.strokeStyle = "#254e1c";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Central vein
      ctx.beginPath();
      ctx.moveTo(0, 200);
      ctx.quadraticCurveTo(-4, 0, 0, -205);
      ctx.strokeStyle = "#80b870";
      ctx.lineWidth = 3.5;
      ctx.stroke();

      // Lateral veins
      for (var y = 140; y > -160; y -= 40) {
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = "rgba(128,184,112,0.6)";
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.quadraticCurveTo(-50, y - 20, -110, y - 35);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.quadraticCurveTo(50, y - 20, 110, y - 35);
        ctx.stroke();
      }

      // Late blight dark water-soaked patches
      var lesions = [
        { x: -55, y: -50, rx: 38, ry: 30, rot: 0.3 },
        { x: 50, y: 25, rx: 46, ry: 34, rot: -0.2 },
        { x: -25, y: 70, rx: 34, ry: 26, rot: 0.1 }
      ];
      lesions.forEach(function (l) {
        ctx.save();
        ctx.translate(l.x, l.y);
        ctx.rotate(l.rot);
        ctx.beginPath();
        ctx.ellipse(0, 0, l.rx + 10, l.ry + 8, 0, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(163, 190, 140, 0.6)";
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(0, 0, l.rx, l.ry, 0, 0, Math.PI * 2);
        ctx.fillStyle = "#33221b";
        ctx.fill();
        ctx.beginPath();
        ctx.ellipse(0, 0, l.rx * 0.7, l.ry * 0.7, 0, 0, Math.PI * 2);
        ctx.fillStyle = "#1c1410";
        ctx.fill();
        ctx.restore();
      });

    } else if (sampleType === "apple_healthy") {
      // Clean healthy apple leaf
      ctx.beginPath();
      ctx.moveTo(0, 210);
      ctx.bezierCurveTo(-140, 140, -150, -90, 0, -220);
      ctx.bezierCurveTo(150, -90, 140, 140, 0, 210);
      ctx.closePath();
      var aGrad = ctx.createLinearGradient(0, -220, 0, 210);
      aGrad.addColorStop(0, "#3ca33c");
      aGrad.addColorStop(0.5, "#46b646");
      aGrad.addColorStop(1, "#2e882e");
      ctx.fillStyle = aGrad;
      ctx.fill();
      ctx.strokeStyle = "#206620";
      ctx.lineWidth = 2.2;
      ctx.stroke();

      // Central vein
      ctx.beginPath();
      ctx.moveTo(0, 210);
      ctx.quadraticCurveTo(-3, 0, 0, -215);
      ctx.strokeStyle = "#8ae08a";
      ctx.lineWidth = 3.5;
      ctx.stroke();

      // Lateral pinnate veins
      for (var ay = 150; ay > -170; ay -= 36) {
        ctx.lineWidth = 1.8;
        ctx.strokeStyle = "rgba(138, 224, 138, 0.7)";
        ctx.beginPath();
        ctx.moveTo(0, ay);
        ctx.quadraticCurveTo(-45, ay - 18, -105, ay - 30);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, ay);
        ctx.quadraticCurveTo(45, ay - 18, 105, ay - 30);
        ctx.stroke();
      }

    } else {
      // Default: Tomato Early Blight
      ctx.beginPath();
      ctx.moveTo(0, 200);
      ctx.bezierCurveTo(-135, 120, -145, -70, 0, -210);
      ctx.bezierCurveTo(145, -70, 135, 120, 0, 200);
      ctx.closePath();
      var tGrad = ctx.createLinearGradient(-110, 0, 110, 0);
      tGrad.addColorStop(0, "#4a8a38");
      tGrad.addColorStop(0.5, "#559c40");
      tGrad.addColorStop(1, "#3c752c");
      ctx.fillStyle = tGrad;
      ctx.fill();
      ctx.strokeStyle = "#2c5a1f";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Veins
      ctx.beginPath();
      ctx.moveTo(0, 200);
      ctx.quadraticCurveTo(-3, 0, 0, -205);
      ctx.strokeStyle = "#88c278";
      ctx.lineWidth = 3;
      ctx.stroke();
      for (var ty = 130; ty > -150; ty -= 38) {
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = "rgba(136, 194, 120, 0.6)";
        ctx.beginPath();
        ctx.moveTo(0, ty);
        ctx.quadraticCurveTo(-40, ty - 18, -95, ty - 28);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, ty);
        ctx.quadraticCurveTo(40, ty - 18, 95, ty - 28);
        ctx.stroke();
      }

      // Early blight concentric target rings
      var targets = [
        { x: -40, y: -35, r: 30 },
        { x: 38, y: 35, r: 36 },
        { x: -18, y: 95, r: 24 }
      ];
      targets.forEach(function (tgt) {
        ctx.save();
        ctx.translate(tgt.x, tgt.y);
        ctx.beginPath();
        ctx.arc(0, 0, tgt.r + 9, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(225, 195, 45, 0.55)";
        ctx.fill();
        for (var ring = tgt.r; ring > 4; ring -= 6) {
          ctx.beginPath();
          ctx.arc(0, 0, ring, 0, Math.PI * 2);
          ctx.fillStyle = (ring % 12 === 0) ? "#4a2a16" : "#2b180d";
          ctx.fill();
          ctx.strokeStyle = "#6b3f20";
          ctx.lineWidth = 1.4;
          ctx.stroke();
        }
        ctx.restore();
      });
    }

    ctx.restore();

    canvas.toBlob(function (blob) {
      if (!blob) return;
      var file = new File([blob], "sample-" + sampleType + ".jpg", { type: "image/jpeg" });
      handleFile(file);
    }, "image/jpeg", 0.92);
  }

  /* ---------- theme / language / banner ---------- */
  function isDark() {
    var th = document.documentElement.getAttribute("data-theme");
    if (th) return th === "dark";
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }
  function syncThemeButton() { $("btnTheme").setAttribute("aria-pressed", String(isDark())); }
  function toggleTheme() {
    var next = isDark() ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try { localStorage.setItem("cd.theme", next); } catch (e) { /* ignore */ }
    syncThemeButton();
  }
  function renderDemoBanner() {
    var on = CFG.MOCK || !!(state.result && state.result.mock);
    var b = $("demoBanner"); b.hidden = !on; if (on) b.textContent = t("demo_banner");
  }
  function renderStatic() {
    $("dzHint").textContent = t("dz_hint", { mb: CFG.MAX_UPLOAD_MB });
    $("footerNote").textContent = t("footer_note");
    renderDemoBanner();
  }
  function renderAll() {
    renderStatic(); renderHints(); renderError();
    if (state.previewUrl) $("previewImg").alt = t("preview_alt");
    if (state.result) renderResult();
  }

  /* ---------- reset ---------- */
  function resetAll() {
    if (state.abort) { state.abort.abort(); state.abort = null; }
    stopLoadingText(); revokePreview();
    state.file = null; state.result = null; state.quality = []; state.resized = false; state.error = null; state.heatSrc = null;
    $("fileInput").value = ""; $("captureInput").value = ""; $("previewImg").removeAttribute("src");
    var sticky = $("resultStickyBar");
    if (sticky) sticky.hidden = true;
    renderDemoBanner();
    showView("input", $("dropzone"));
  }

  /* ---------- events ---------- */
  function hasFiles(e) { return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], "Files") !== -1; }

  function handleScroll() {
    var sticky = $("resultStickyBar");
    if (!sticky) return;
    if (state.view === "result") {
      var sc = $("statusCard");
      var rect = sc ? sc.getBoundingClientRect() : null;
      var passedTop = rect ? (rect.bottom < 60) : (window.scrollY > 280);
      sticky.hidden = !passedTop;
    } else {
      sticky.hidden = true;
    }
  }

  function bind() {
    var dz = $("dropzone");
    $("btnChoose").addEventListener("click", function (e) { e.stopPropagation(); $("fileInput").click(); });
    $("btnCapture").addEventListener("click", function (e) { e.stopPropagation(); onCapture(); });
    dz.addEventListener("click", function (e) { if (!e.target.closest("button")) $("fileInput").click(); });
    dz.addEventListener("keydown", function (e) { if ((e.key === "Enter" || e.key === " ") && e.target === dz) { e.preventDefault(); $("fileInput").click(); } });
    ["dragenter", "dragover"].forEach(function (ev) { dz.addEventListener(ev, function (e) { if (hasFiles(e)) { e.preventDefault(); dz.classList.add("is-drag"); } }); });
    ["dragleave", "drop"].forEach(function (ev) { dz.addEventListener(ev, function () { dz.classList.remove("is-drag"); }); });
    dz.addEventListener("drop", function (e) { if (hasFiles(e)) { e.preventDefault(); handleFile(e.dataTransfer.files[0]); } });
    window.addEventListener("dragover", function (e) { if (hasFiles(e)) e.preventDefault(); });     /* a missed drop must not open the file in the tab */
    window.addEventListener("drop", function (e) { if (hasFiles(e)) e.preventDefault(); });
    ["fileInput", "captureInput"].forEach(function (id) {
      $(id).addEventListener("change", function (e) { var f = e.target.files && e.target.files[0]; e.target.value = ""; handleFile(f); });
    });
    document.addEventListener("paste", function (e) {
      if (state.view !== "input" && state.view !== "preview") return;
      var f = e.clipboardData && e.clipboardData.files && e.clipboardData.files[0];
      if (f && /^image\//.test(f.type)) { e.preventDefault(); handleFile(f); }
    });

    $("btnAnalyse").addEventListener("click", analyse);
    $("btnChange").addEventListener("click", resetAll);
    $("btnCancel").addEventListener("click", function () { if (state.abort) state.abort.abort(); });
    $("btnRetry").addEventListener("click", function () { var r = state.error && state.error.retry; if (r) r(); });
    $("btnErrBack").addEventListener("click", resetAll);

    // All "Test another leaf" buttons (Top, Sticky, End, Header)
    ["btnNew", "btnNewTop", "btnNewSticky", "btnNewHeader"].forEach(function (id) {
      var b = $(id);
      if (b) b.addEventListener("click", resetAll);
    });

    // Make Step 1 in the stepper clickable to test a new photo
    var step1 = $("steps").querySelector('[data-step="1"]');
    if (step1) {
      step1.addEventListener("click", function () {
        if (state.view !== "input") resetAll();
      });
      step1.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (state.view !== "input") resetAll();
        }
      });
    }

    // Print report
    var btnPrint = $("btnPrintReport");
    if (btnPrint) {
      btnPrint.addEventListener("click", function () { window.print(); });
    }

    // Back to top
    var btnTop = $("btnBackToTop");
    if (btnTop) {
      btnTop.addEventListener("click", function () {
        try { $("diagnose").scrollIntoView({ block: "start", behavior: "smooth" }); } catch (e) { window.scrollTo(0, 0); }
      });
    }

    // Sample leaf clicks
    var sampleSec = $("sampleSection");
    if (sampleSec) {
      sampleSec.addEventListener("click", function (e) {
        var btn = e.target.closest("button.sample-chip");
        if (!btn) return;
        var sType = btn.getAttribute("data-sample");
        if (sType) generateSampleLeaf(sType);
      });
    }

    $("predList").addEventListener("click", function (e) {
      var b = e.target.closest("button.pred"); if (!b) return;
      state.selected = Number(b.getAttribute("data-i")); state.kbOpen = true;
      renderPredictions(); renderKB();
    });
    $("vizOriginal").addEventListener("click", function () { state.vizMode = "photo"; renderViz(); });
    $("vizGradcam").addEventListener("click", function () { state.vizMode = "cam"; renderViz(); });
    $("opacity").addEventListener("input", function (e) { state.opacity = Number(e.target.value) / 100; $("vizHeat").style.opacity = String(state.opacity); });

    $("fbYes").addEventListener("click", function () { submitFeedback(true, null); });
    $("fbNo").addEventListener("click", function () { state.fb.wrong = true; state.fb.status = null; renderFeedback(); $("fbSelect").focus(); });
    $("fbSelect").addEventListener("change", function () { $("fbSend").disabled = !$("fbSelect").value || state.fb.busy; });
    $("fbSend").addEventListener("click", function () { var v = $("fbSelect").value; if (v) submitFeedback(false, v === "__unknown__" ? null : v); });

    var dlg = $("cameraDialog");
    $("camClose").addEventListener("click", function () { if (dlg.open) dlg.close(); });
    $("camShot").addEventListener("click", shoot);
    $("camSwitch").addEventListener("click", switchCamera);
    dlg.addEventListener("close", stopStream);

    $("btnLang").addEventListener("click", function () { I.setLang(I.getLang() === "ar" ? "en" : "ar", true); });
    $("btnTheme").addEventListener("click", toggleTheme);
    document.addEventListener("cd:langchange", renderAll);
    window.addEventListener("pagehide", stopStream);
    window.addEventListener("scroll", handleScroll, { passive: true });
  }

  function init() {
    $("fileInfo").setAttribute("dir", "auto");
    I.setLang(I.detect(CFG.DEFAULT_LANG), false);
    syncThemeButton();
    bind();
    renderStatic();
    showView("input");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();

  /* tiny surface for automated tests */
  window.CD_APP = { state: state, handleFile: handleFile, analyse: analyse, cfg: CFG, displayName: displayName, resetAll: resetAll, generateSampleLeaf: generateSampleLeaf };
})();
