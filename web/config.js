/* Deployment settings - edit this file only; no need to touch the application code. */
window.APP_CONFIG = {
  // "" = same origin as the page. For Vercel, set this to the Azure Container Apps URL:
  //   API_BASE: "https://ai-crop-doctor-api.<region>.azurecontainerapps.io"
  API_BASE: "",
  PREDICT_PATH: "/api/predict",  // POST multipart/form-data, field "file"
  FEEDBACK_PATH: "/api/feedback",// POST application/json
  MOCK: false,                   // true = simulated results in the browser (also: open the page with ?mock=1)
  MAX_UPLOAD_MB: 10,
  ACCEPTED_TYPES: ["image/jpeg", "image/png", "image/webp"],
  CONFIDENCE_THRESHOLD: 0.60,    // must match CONFIDENCE_THRESHOLD on the Azure API ("uncertain" flag overrides this)
  REQUEST_TIMEOUT_MS: 30000,
  FEEDBACK_ENABLED: true,
  DEFAULT_LANG: "auto"           // "auto" | "en" | "ar"
};
