# AI Crop Doctor - Streamlit app (UI demo)

Streamlit front end that copies the look and EN/AR text of `web/`.

- Run: `pip install -r requirements.txt && streamlit run app.py`
- Predictions: set `API_URL` to the FastAPI service (`azure/main.py`, `POST /api/predict`). Without it the app shows no diagnosis (it never invents one).
- Grad-CAM: not available for the current model (frozen CLIP + DINOv2 features), shown as a labelled placeholder.
- `samples/`: 11 PlantVillage lab photos (spMohanty/PlantVillage-Dataset), one per diagnosed class. Demo only, not a test set.
- Class list comes from the project results deck and is to be confirmed against the final run.
