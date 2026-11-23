/* API layer: calls the FastAPI backend, validates/normalises its answer, and provides a browser-only mock for demos.
   Expected contract: see README.md ("API contract"). */
(function () {
  "use strict";

  function apiError(code, status) {
    var e = new Error(code); e.name = "ApiError"; e.code = code; e.status = status || null; return e;
  }

  function endpoint(cfg, path) { return String(cfg.API_BASE || "").replace(/\/+$/, "") + path; }

  /* Only allow image sources that cannot run script: data:image/*, http(s) URLs and same-origin paths. */
  function safeImageSrc(v) {
    if (typeof v !== "string") return null;
    v = v.trim();
    if (!v) return null;
    if (/^data:image\/(png|jpe?g|webp);base64,[A-Za-z0-9+\/=\s]+$/i.test(v)) return v;
    if (/^https?:\/\//i.test(v)) return v;
    if (v.charAt(0) === "/" && v.charAt(1) !== "/") return v;
    if (/^[A-Za-z0-9+\/=\s]{200,}$/.test(v)) return "data:image/png;base64," + v.replace(/\s+/g, "");
    return null;
  }

  /* Preprocessing report: step list + previews of what the model actually received. */
  function normalizePreprocess(p) {
    if (!p || typeof p !== "object" || !Array.isArray(p.steps)) return null;
    var steps = [];
    p.steps.forEach(function (s) {
      if (!s || typeof s !== "object" || typeof s.id !== "string" || !s.id) return;
      steps.push({
        id: s.id,
        label: typeof s.label === "string" ? s.label : s.id,
        detail: typeof s.detail === "string" ? s.detail : "",
        preview: safeImageSrc(s.preview)
      });
    });
    if (!steps.length) return null;
    return {
      steps: steps,
      input: (p.input && typeof p.input === "object") ? p.input : null,
      recipe: (p.recipe && typeof p.recipe === "object") ? p.recipe : null
    };
  }

  function normalize(raw, cfg) {
    if (!raw || typeof raw !== "object") throw apiError("bad_response");
    var list = raw.predictions || raw.top3 || raw.results;
    if (!Array.isArray(list) || !list.length) throw apiError("bad_response");
    var preds = [];
    list.forEach(function (p) {
      if (!p || typeof p !== "object") return;
      var label = (p.label !== undefined ? p.label : (p.class_name !== undefined ? p.class_name : (p["class"] !== undefined ? p["class"] : p.name)));
      var conf = Number(p.confidence !== undefined ? p.confidence : (p.probability !== undefined ? p.probability : p.score));
      if (typeof label !== "string" || !label || !isFinite(conf)) return;
      if (conf > 1 && conf <= 100) conf = conf / 100;
      conf = Math.min(Math.max(conf, 0), 1);
      preds.push({ label: label, confidence: conf, classId: (p.class_id !== undefined ? p.class_id : (p.id !== undefined ? p.id : null)) });
    });
    if (!preds.length) throw apiError("bad_response");
    preds.sort(function (a, b) { return b.confidence - a.confidence; });
    preds = preds.slice(0, 3);
    var uncertain = (typeof raw.uncertain === "boolean") ? raw.uncertain : (preds[0].confidence < cfg.CONFIDENCE_THRESHOLD);
    var g = raw.gradcam;
    var overlay = (typeof g === "string") ? g : (g && g.overlay);
    if (!overlay) overlay = raw.gradcam_overlay || raw.gradcam_image || null;
    var heatmap = (g && typeof g === "object" && g.heatmap) || raw.gradcam_heatmap || null;
    return {
      requestId: raw.request_id || raw.id || null,
      predictions: preds,
      uncertain: uncertain,
      preprocess: normalizePreprocess(raw.preprocess),
      gradcam: { overlay: safeImageSrc(overlay), heatmap: safeImageSrc(heatmap) },
      modelVersion: raw.model_version || null,
      latencyMs: isFinite(Number(raw.latency_ms)) && raw.latency_ms !== null ? Number(raw.latency_ms) : null,
      mock: raw.mock === true
    };
  }

  /* fetch with timeout + user abort; returns parsed JSON. Maps every failure to an ApiError code. */
  function requestJson(cfg, path, init, opts) {
    var ctrl = new AbortController(), timedOut = false, userSignal = opts && opts.signal;
    var onAbort = function () { ctrl.abort(); };
    if (userSignal) { if (userSignal.aborted) ctrl.abort(); else userSignal.addEventListener("abort", onAbort); }
    var timer = setTimeout(function () { timedOut = true; ctrl.abort(); }, cfg.REQUEST_TIMEOUT_MS);
    var cleanup = function () { clearTimeout(timer); if (userSignal) userSignal.removeEventListener("abort", onAbort); };
    init = Object.assign({}, init, { signal: ctrl.signal });
    return fetch(endpoint(cfg, path), init).then(function (res) {
      if (!res.ok) {
        var c = (res.status === 413 || res.status === 415 || res.status === 422 || res.status === 429) ? ("http_" + res.status) : (res.status >= 500 ? "server" : "http_" + res.status);
        throw apiError(c, res.status);
      }
      return res.json().catch(function () { throw apiError("bad_response"); });
    }).then(function (data) { cleanup(); return data; }, function (err) {
      cleanup();
      if (err && err.name === "ApiError") throw err;
      if (err && err.name === "AbortError") throw apiError(timedOut ? "timeout" : "aborted");
      throw apiError("network");
    });
  }

  function predict(file, cfg, opts) {
    if (cfg.MOCK) return mockPredict(file, cfg, opts);
    var fd = new FormData();
    fd.append("file", file, file.name || "leaf.jpg");
    return requestJson(cfg, cfg.PREDICT_PATH, { method: "POST", body: fd }, opts).then(function (raw) { return normalize(raw, cfg); });
  }

  function sendFeedback(payload, cfg, opts) {
    if (cfg.MOCK) return delay(400, opts && opts.signal).then(function () { return { status: "ok" }; });
    return requestJson(cfg, cfg.FEEDBACK_PATH, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }, opts);
  }

  /* ---------------- mock (demo) ---------------- */
  function delay(ms, signal) {
    return new Promise(function (resolve, reject) {
      var t = setTimeout(resolve, ms);
      if (signal) signal.addEventListener("abort", function () { clearTimeout(t); reject(apiError("aborted")); });
    });
  }
  function hash(str) { var h = 2166136261; for (var i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  function mockHeatmap(file, seed) {
    return new Promise(function (resolve) {
      setTimeout(function () { resolve(null); }, 3000);   /* never let a slow/failed image decode block the demo */
      try {
        var url = URL.createObjectURL(file), img = new Image();
        img.onload = function () {
          URL.revokeObjectURL(url);
          try {
            var s = Math.min(1, 512 / Math.max(img.naturalWidth, img.naturalHeight));
            var w = Math.max(16, Math.round(img.naturalWidth * s)), h = Math.max(16, Math.round(img.naturalHeight * s));
            var c = document.createElement("canvas"); c.width = w; c.height = h;
            var ctx = c.getContext("2d");
            var cx = w * (0.35 + ((seed % 31) / 100)), cy = h * (0.35 + (((seed >>> 5) % 31) / 100)), r = Math.min(w, h) * 0.38;
            var g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
            g.addColorStop(0, "rgba(230,30,30,0.95)"); g.addColorStop(0.45, "rgba(255,190,30,0.75)"); g.addColorStop(1, "rgba(255,255,0,0)");
            ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
            resolve(c.toDataURL("image/png"));
          } catch (e) { resolve(null); }
        };
        img.onerror = function () { URL.revokeObjectURL(url); resolve(null); };
        img.src = url;
      } catch (e) { resolve(null); }
    });
  }

  function mockPredict(file, cfg, opts) {
    var signal = opts && opts.signal;
    return delay(900, signal).then(function () {
      var keys = Object.keys((window.CD_KB && window.CD_KB.conditions) || {});
      if (keys.length < 3) throw apiError("bad_response");
      var h = hash((file.name || "") + ":" + file.size);
      var idx = [h % keys.length, (h >>> 7) % keys.length, (h >>> 13) % keys.length];
      while (idx[1] === idx[0]) idx[1] = (idx[1] + 1) % keys.length;
      while (idx[2] === idx[0] || idx[2] === idx[1]) idx[2] = (idx[2] + 1) % keys.length;
      var low = (h % 5 === 0);   // about 1 in 5 files demonstrates the "not sure" screen
      var conf = low ? [0.46, 0.27, 0.14] : [0.93 - (h % 7) / 100, 0.04, 0.01];
      return mockHeatmap(file, h).then(function (heat) {
        return normalize({
          request_id: "demo-" + h.toString(16), mock: true, model_version: "demo",
          predictions: idx.map(function (i, n) { return { label: keys[i], confidence: conf[n] }; }),
          gradcam: { heatmap: heat }, latency_ms: 900
        }, cfg);
      });
    });
  }

  window.CD_API = { predict: predict, sendFeedback: sendFeedback, normalize: normalize, safeImageSrc: safeImageSrc, apiError: apiError };
})();
