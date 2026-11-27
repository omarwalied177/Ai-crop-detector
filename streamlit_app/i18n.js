/* UI strings (English / Arabic) and language handling. Disease names and guidance live in kb-data.js. */
(function () {
  "use strict";
  var STR = {
    en: {
      skip: "Skip to main content", app_name: "AI Crop Doctor",
      lang_aria: "Switch language to Arabic", theme_aria: "Toggle dark mode",
      hero_badge: "AI Plant Health Assistant",
      hero_title: "Photograph one leaf. Get an instant diagnosis.",
      hero_sub: "Upload or capture a clear photo of a plant leaf. The model suggests the three most likely conditions, shows which part of the leaf it looked at, and explains practical treatment steps.",
      diagnose_heading: "Diagnose a leaf",
      step_photo: "Photo", step_analyse: "Analysis", step_result: "Result",
      dz_aria: "Choose a leaf photo. Press Enter to browse files.", dz_title: "Drop a leaf photo here", dz_or: "or",
      btn_choose: "Upload a photo", btn_capture: "Take a photo", dz_hint: "JPG, PNG or WebP, up to {mb} MB",
      try_samples_title: "Don't have a leaf photo? Click a sample to test:",
      sample_tomato_early_blight: "Tomato - Early blight",
      sample_corn_rust: "Corn - Common rust",
      sample_potato_late_blight: "Potato - Late blight",
      sample_apple_healthy: "Apple - Healthy leaf",
      tips_title: "For the most reliable result",
      tip_single_title: "Single Leaf", tip_1: "Show one leaf and fill most of the frame with it.",
      tip_light_title: "Natural Light", tip_2: "Use daylight and avoid strong shadows or glare.",
      tip_focus_title: "Sharp Focus", tip_3: "Hold the camera steady and keep the leaf in focus.",
      tip_bg_title: "Plain Background", tip_4: "A plain background works best.",
      privacy_note: "Upload leaf photos only. Avoid people or personal information in the picture.",
      preview_title: "Check your photo", preview_alt: "Preview of the selected leaf photo",
      btn_analyse: "Analyse leaf", btn_change: "Choose another photo", btn_other_photo: "Choose another photo",
      hint_dark: "The photo looks dark. Move to better light if you can.",
      hint_bright: "The photo looks very bright. Avoid direct glare on the leaf.",
      hint_blur: "The photo may be out of focus. Hold the camera steady and tap the leaf to focus.",
      hint_small: "The photo is small ({w} × {h} px). A larger photo gives better results.",
      hint_resized: "The photo was larger than {mb} MB, so it was reduced in size before upload.",
      loading_title: "Analysing your leaf", load_1: "Uploading & inspecting photo", load_2: "Comparing leaf features with 38 conditions", load_3: "Generating Grad-CAM visual explanation", btn_cancel: "Cancel",
      error_title: "The photo could not be analysed",
      err_type: "This file type is not supported. Use a JPG, PNG or WebP image.",
      err_size: "The photo is larger than {mb} MB. Choose a smaller photo.",
      err_decode: "This image could not be opened. Choose a different photo.",
      err_network: "The server could not be reached. Check your connection and try again.",
      err_timeout: "The analysis took too long. Try again.",
      err_server: "The server had a problem. Wait a moment and try again.",
      err_413: "The server rejected the photo because it is too large.",
      err_415: "The server does not support this image type. Use JPG, PNG or WebP.",
      err_422: "The server could not read this image. Choose a different photo.",
      err_429: "Too many requests. Wait a moment and try again.",
      err_bad_response: "The server sent a response the page could not read.",
      err_cam_denied: "Camera access was blocked. Allow the camera in your browser settings, or upload a photo instead.",
      err_cam_none: "No camera was found on this device. Upload a photo instead.",
      err_cam_generic: "The camera could not be started. Upload a photo instead.",
      btn_retry: "Try again",
      result_ready_badge: "Analysis complete",
      result_overview_title: "Diagnosis Results",
      res_ok_title: "Most likely: {name}", res_ok_msg: "Confidence {pct}. Read the guidance below and confirm with an expert before treating.",
      res_healthy_title: "The leaf looks healthy", res_healthy_msg: "Most likely {name}, confidence {pct}.",
      res_unsure_title: "The model is not sure about this photo",
      res_unsure_msg: "Confidence is only {pct}, so the conditions listed are possibilities, not a diagnosis. Take a clearer photo of a single leaf and ask an agricultural extension officer before acting.",
      rank_heading: "Most likely conditions", pred_select_aria: "Show information about {name}",
      rank_hint: "💡 Click any condition to view symptoms and treatment guide below",
      conf_aria: "Confidence {pct}",
      gc_view_aria: "Image view", gc_original: "Photo", gc_overlay: "Grad-CAM", gc_strength: "Overlay",
      gc_caption: "Grad-CAM marks the parts of the leaf that influenced the top prediction most (warm colours). It helps you check what the model looked at; it does not prove the cause.",
      gc_none: "A Grad-CAM view is not available for this result.",
      prep_title: "Preprocessing",
      prep_sub: "Exactly what happens between your upload and the model, the same steps used in training.",
      prep_decode_t: "Decode & orient", prep_clip_resize_t: "CLIP input", prep_dino_resize_t: "DINOv2 input",
      prep_normalize_t: "Normalize", prep_features_t: "Feature extraction", prep_views_t: "Views",
      prep_alt: "Step {n} of preprocessing: {step}",
      gc_alt_photo: "Your leaf photo", gc_alt_cam: "Grad-CAM view of your leaf photo",
      kb_pick: "Select a possibility above to read about it.",
      kb_symptoms: "Symptoms", kb_cause: "Cause", kb_management: "Management & Treatment", kb_prevention: "Prevention",
      kb_agent: "Causal agent", kb_none: "No guidance is available for this condition yet. Ask your local agricultural extension service.",
      kb_sources: "Sources", kb_key: "Good to know",
      type_fungal: "Fungal disease", type_bacterial: "Bacterial disease", type_viral: "Viral disease",
      type_oomycete: "Water-mould disease (oomycete)", type_pest: "Pest (mite)", type_healthy: "Healthy",
      cause_healthy: "No disease detected.",
      disclaimer: "This tool supports decisions and does not replace an agricultural expert. Confirm the diagnosis with a qualified agronomist or your local agricultural extension service before applying any treatment.",
      meta_model: "Model {v}", meta_time: "{ms} ms",
      fb_title: "Was this correct?", fb_yes: "Yes", fb_no: "No", fb_select_label: "What is the correct condition?",
      fb_choose: "Choose the correct condition", fb_unknown: "Not sure / not in the list", fb_send: "Send feedback",
      fb_sending: "Sending…", fb_thanks: "Thank you. Your feedback helps improve the model.", fb_error: "The feedback could not be sent. Try again.",
      btn_new: "Test another leaf",
      btn_new_short: "New test",
      btn_print: "Print report",
      btn_back_to_top: "Top",
      how_title: "How it works",
      how_1_t: "Add a photo", how_1_d: "Upload an image or take one with your camera.",
      how_2_t: "The model compares it", how_2_d: "The photo is compared with 11 conditions across 5 crops (12 crops are recognized), including healthy leaves.",
      how_3_t: "Read, then verify", how_3_d: "See the top three possibilities, what the model focused on, and practical guidance to discuss with an expert.",
      footer_note: "AI Crop Doctor, graduation project.",
      demo_banner: "Demo mode: these results are simulated and must not be used for decisions.",
      cam_title: "Take a photo", cam_close: "Close", cam_capture: "Capture", cam_switch: "Switch camera", cam_starting: "Starting the camera…", cam_ready: "Centre the leaf in the frame, then capture."
    },
    ar: {
      skip: "انتقل إلى المحتوى الرئيسي", app_name: "دكتور المحاصيل",
      lang_aria: "تغيير اللغة إلى الإنجليزية", theme_aria: "تبديل الوضع الداكن",
      hero_badge: "مساعد صحة النبات بالذكاء الاصطناعي",
      hero_title: "صوّر ورقة واحدة واحصل على تشخيص فوري.",
      hero_sub: "ارفع صورة واضحة لورقة نبات أو التقطها بالكاميرا. يقترح النموذج أكثر ثلاث حالات احتمالًا، ويُظهر الجزء الذي ركّز عليه من الورقة، ويشرح خطوات العلاج العملية.",
      diagnose_heading: "تشخيص ورقة نبات",
      step_photo: "الصورة", step_analyse: "التحليل", step_result: "النتيجة",
      dz_aria: "اختر صورة ورقة نبات. اضغط Enter لتصفّح الملفات.", dz_title: "أفلت صورة الورقة هنا", dz_or: "أو",
      btn_choose: "رفع صورة", btn_capture: "التقاط صورة", dz_hint: "JPG أو PNG أو WebP، حتى {mb} ميجابايت",
      try_samples_title: "ليس لديك صورة ورقة؟ جرّب نموذجاً جاهزاً:",
      sample_tomato_early_blight: "طماطم - لفحة مبكرة",
      sample_corn_rust: "ذرة - صدأ شائع",
      sample_potato_late_blight: "بطاطس - لفحة متأخرة",
      sample_apple_healthy: "تفاح - ورقة سليمة",
      tips_title: "للحصول على نتيجة دقيقة وموثوقة",
      tip_single_title: "ورقة واحدة", tip_1: "صوّر ورقة واحدة واجعلها تملأ معظم الإطار.",
      tip_light_title: "إضاءة طبيعية", tip_2: "استخدم ضوء النهار وتجنّب الظلال القوية والانعكاسات.",
      tip_focus_title: "تركيز واضح", tip_3: "ثبّت الكاميرا وتأكد أن الورقة واضحة وغير مهزوزة.",
      tip_bg_title: "خلفية محايدة", tip_4: "الخلفية البسيطة تعطي أفضل نتيجة.",
      privacy_note: "ارفع صور الأوراق فقط، وتجنّب ظهور أشخاص أو معلومات شخصية في الصورة.",
      preview_title: "راجع الصورة", preview_alt: "معاينة صورة الورقة المختارة",
      btn_analyse: "حلّل الورقة", btn_change: "اختر صورة أخرى", btn_other_photo: "اختر صورة أخرى",
      hint_dark: "الصورة تبدو مظلمة. انتقل إلى إضاءة أفضل إن أمكن.",
      hint_bright: "الصورة شديدة السطوع. تجنّب الانعكاس المباشر للضوء على الورقة.",
      hint_blur: "قد تكون الصورة غير واضحة. ثبّت الكاميرا واضغط على الورقة لضبط التركيز.",
      hint_small: "الصورة صغيرة ({w} × {h} بكسل). الصورة الأكبر تعطي نتائج أفضل.",
      hint_resized: "كان حجم الصورة أكبر من {mb} ميجابايت، فتم تصغيرها قبل الرفع.",
      loading_title: "جارٍ تحليل الورقة", load_1: "جارٍ فحص وتحضير الصورة", load_2: "جارٍ مقارنة خصائص الورقة بـ 38 حالة", load_3: "جارٍ تجهيز الشرح المرئي عبر Grad-CAM", btn_cancel: "إلغاء",
      error_title: "تعذّر تحليل الصورة",
      err_type: "نوع الملف غير مدعوم. استخدم صورة بصيغة JPG أو PNG أو WebP.",
      err_size: "حجم الصورة أكبر من {mb} ميجابايت. اختر صورة أصغر.",
      err_decode: "تعذّر فتح هذه الصورة. اختر صورة مختلفة.",
      err_network: "تعذّر الوصول إلى الخادم. تحقق من اتصالك بالإنترنت وحاول مرة أخرى.",
      err_timeout: "استغرق التحليل وقتًا طويلًا. حاول مرة أخرى.",
      err_server: "حدثت مشكلة في الخادم. انتظر قليلًا ثم حاول مرة أخرى.",
      err_413: "رفض الخادم الصورة لأن حجمها كبير جدًا.",
      err_415: "الخادم لا يدعم نوع هذه الصورة. استخدم JPG أو PNG أو WebP.",
      err_422: "تعذّر على الخادم قراءة هذه الصورة. اختر صورة مختلفة.",
      err_429: "عدد الطلبات كبير. انتظر قليلًا ثم حاول مرة أخرى.",
      err_bad_response: "أرسل الخادم ردًّا لم تتمكن الصفحة من قراءته.",
      err_cam_denied: "تم حظر الوصول إلى الكاميرا. اسمح بالكاميرا من إعدادات المتصفح، أو ارفع صورة بدلًا من ذلك.",
      err_cam_none: "لم يتم العثور على كاميرا في هذا الجهاز. ارفع صورة بدلًا من ذلك.",
      err_cam_generic: "تعذّر تشغيل الكاميرا. ارفع صورة بدلًا من ذلك.",
      btn_retry: "حاول مرة أخرى",
      result_ready_badge: "اكتمل التشخيص",
      result_overview_title: "نتائج التشخيص",
      res_ok_title: "الأرجح: {name}", res_ok_msg: "نسبة الثقة {pct}. اقرأ الإرشادات أدناه وتأكد من خبير قبل أي علاج.",
      res_healthy_title: "الورقة تبدو سليمة", res_healthy_msg: "الأرجح {name}، بنسبة ثقة {pct}.",
      res_unsure_title: "النموذج غير متأكد من هذه الصورة",
      res_unsure_msg: "نسبة الثقة {pct} فقط، لذلك فالحالات المعروضة مجرد احتمالات وليست تشخيصًا. التقط صورة أوضح لورقة واحدة واسأل مرشدًا زراعيًا قبل اتخاذ أي إجراء.",
      rank_heading: "الحالات الأكثر احتمالًا", pred_select_aria: "عرض معلومات عن {name}",
      rank_hint: "💡 اضغط على أي حالة لعرض الأعراض وخطة العلاج بالأسفل",
      conf_aria: "نسبة الثقة {pct}",
      gc_view_aria: "عرض الصورة", gc_original: "الصورة", gc_overlay: "Grad-CAM", gc_strength: "الطبقة",
      gc_caption: "تُظهر Grad-CAM أجزاء الورقة التي أثّرت أكثر في التوقع الأول (الألوان الدافئة). تساعدك على فهم ما ركّز عليه النموذج، لكنها لا تثبت سبب المشكلة.",
      gc_none: "عرض Grad-CAM غير متاح لهذه النتيجة.",
      prep_title: "المعالجة المسبقة",
      prep_sub: "ما يحدث بين رفع الصورة ودخولها إلى النموذج، بنفس خطوات التدريب.",
      prep_decode_t: "فك الترميز وتصحيح الاتجاه", prep_clip_resize_t: "مدخل CLIP", prep_dino_resize_t: "مدخل DINOv2",
      prep_normalize_t: "التطبيع", prep_features_t: "استخراج السمات", prep_views_t: "النسخ المستخدمة",
      prep_alt: "الخطوة {n} من المعالجة: {step}",
      gc_alt_photo: "صورة الورقة", gc_alt_cam: "عرض Grad-CAM لصورة الورقة",
      kb_pick: "اختر أحد الاحتمالات أعلاه لقراءة المعلومات عنه.",
      kb_symptoms: "الأعراض", kb_cause: "السبب", kb_management: "المكافحة والعلاج", kb_prevention: "الوقاية",
      kb_agent: "العامل المسبب", kb_none: "لا توجد إرشادات لهذه الحالة بعد. اسأل مكتب الإرشاد الزراعي المحلي.",
      kb_sources: "المصادر", kb_key: "مهم أن تعرف",
      type_fungal: "مرض فطري", type_bacterial: "مرض بكتيري", type_viral: "مرض فيروسي",
      type_oomycete: "مرض فطريات مائية (أُومايسيت)", type_pest: "آفة (عنكبوت أحمر)", type_healthy: "سليمة",
      cause_healthy: "لم يتم رصد مرض.",
      disclaimer: "هذه الأداة تدعم اتخاذ القرار ولا تغني عن الخبير الزراعي. تأكد من التشخيص مع مهندس زراعي مؤهل أو مكتب الإرشاد الزراعي المحلي قبل تطبيق أي علاج.",
      meta_model: "النموذج {v}", meta_time: "{ms} مللي ثانية",
      fb_title: "هل كانت النتيجة صحيحة؟", fb_yes: "نعم", fb_no: "لا", fb_select_label: "ما هي الحالة الصحيحة؟",
      fb_choose: "اختر الحالة الصحيحة", fb_unknown: "لست متأكدًا / غير موجودة في القائمة", fb_send: "إرسال الملاحظة",
      fb_sending: "جارٍ الإرسال…", fb_thanks: "شكرًا لك. ملاحظتك تساعد في تحسين النموذج.", fb_error: "تعذّر إرسال الملاحظة. حاول مرة أخرى.",
      btn_new: "فحص ورقة أخرى",
      btn_new_short: "فحص جديد",
      btn_print: "طباعة التقرير",
      btn_back_to_top: "للأعلى",
      how_title: "كيف يعمل",
      how_1_t: "أضف صورة", how_1_d: "ارفع صورة أو التقطها بالكاميرا.",
      how_2_t: "يقارنها النموذج", how_2_d: "تُقارن الصورة بـ 11 حالة في 5 محاصيل (يتعرف النموذج على 12 محصولًا)، تشمل الأوراق السليمة.",
      how_3_t: "اقرأ ثم تحقق", how_3_d: "شاهد أكثر ثلاثة احتمالات، وما ركّز عليه النموذج، وإرشادات عملية لمناقشتها مع خبير.",
      footer_note: "دكتور المحاصيل، مشروع تخرج.",
      demo_banner: "وضع تجريبي: هذه النتائج محاكاة ولا يجوز الاعتماد عليها في اتخاذ القرارات.",
      cam_title: "التقاط صورة", cam_close: "إغلاق", cam_capture: "التقاط", cam_switch: "تبديل الكاميرا", cam_starting: "جارٍ تشغيل الكاميرا…", cam_ready: "ضع الورقة في منتصف الإطار ثم التقط الصورة."
    }
  };

  var current = "en";

  function t(key, vars) {
    var table = STR[current] || STR.en;
    var s = (table && table[key] !== undefined) ? table[key] : (STR.en && STR.en[key] !== undefined ? STR.en[key] : key);
    if (vars && typeof s === "string") s = s.replace(/\{(\w+)\}/g, function (m, k) { return (vars[k] !== undefined) ? vars[k] : m; });
    return s;
  }

  function apply(root) {
    root = root || document;
    var q = function (attr, fn) { Array.prototype.forEach.call(root.querySelectorAll("[" + attr + "]"), fn); };
    q("data-i18n", function (el) {
      var key = el.getAttribute("data-i18n");
      var text = t(key);
      if (text && text !== key && !text.startsWith("sample_") && !text.startsWith("try_")) {
        el.textContent = text;
      }
    });
    q("data-i18n-aria", function (el) {
      var key = el.getAttribute("data-i18n-aria");
      var text = t(key);
      if (text && text !== key && !text.startsWith("sample_") && !text.startsWith("try_")) {
        el.setAttribute("aria-label", text);
      }
    });
  }

  function setLang(lang, persist) {
    current = (lang === "ar") ? "ar" : "en";
    var html = document.documentElement;
    html.setAttribute("lang", current);
    html.setAttribute("dir", current === "ar" ? "rtl" : "ltr");
    document.title = t("app_name");
    if (persist !== false) { try { localStorage.setItem("cd.lang", current); } catch (e) { /* storage unavailable */ } }
    apply(document);
    var btn = document.getElementById("btnLangText");
    if (btn) btn.textContent = current === "ar" ? "English" : "العربية";
    document.dispatchEvent(new CustomEvent("cd:langchange", { detail: current }));
  }

  function detect(defaultLang) {
    if (defaultLang === "en" || defaultLang === "ar") return defaultLang;
    try { var saved = localStorage.getItem("cd.lang"); if (saved === "en" || saved === "ar") return saved; } catch (e) { /* ignore */ }
    var nav = (navigator.languages && navigator.languages[0]) || navigator.language || "en";
    return /^ar/i.test(nav) ? "ar" : "en";
  }

  window.CD_I18N = { t: t, apply: apply, setLang: setLang, detect: detect, getLang: function () { return current; }, STR: STR };
})();
