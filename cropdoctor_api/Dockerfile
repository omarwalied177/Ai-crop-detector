FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/opt/hf PIP_NO_CACHE_DIR=1
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
RUN python -c "from huggingface_hub import snapshot_download as d; [d(r, allow_patterns=['*.json','*.safetensors','*.txt','*.model']) for r in ['openai/clip-vit-large-patch14-336','facebook/dinov2-large','google/siglip-so400m-patch14-384']]" && chmod -R a+rX /opt/hf
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app
COPY --chown=user . .
EXPOSE 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
