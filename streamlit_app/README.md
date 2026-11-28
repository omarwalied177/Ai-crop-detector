# AI Crop Doctor - Streamlit app (UI demo)

Streamlit front end that copies the look and the EN/AR text of `web/`.

- Run: `pip install -r requirements.txt && streamlit run app.py`
- Live: https://ai-crop-doctor-omar.streamlit.app/ (UI only: no model connected, so it
  shows no diagnosis)
- Predictions: set `API_URL` to the FastAPI service (`azure/main.py`, `POST
  /api/predict`). Without it the app shows no diagnosis. It never invents one.
- Grad-CAM: not available for the current model (frozen CLIP, DINOv2 and SigLIP
  features with trained heads), shown as a labelled placeholder.
- `samples/`: 11 PlantVillage lab photos (spMohanty/PlantVillage-Dataset), one per
  diagnosed class. Demo only, not a test set.
- The `DIAGNOSED` list in `app.py` covers 5 crops and comes from the project deck. The
  final model has disease heads for 11 crops, so the list needs extending when a model
  is connected.
