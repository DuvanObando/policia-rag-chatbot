# Imagen del motor RAG (FastAPI). Solo instala dependencias: el código de engine/ y corpus/
# se monta desde el repo (ver docker-compose.yml), así los índices y PDFs quedan en el equipo.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/root/.cache/huggingface

# PyTorch solo CPU (evita descargar varios GB de CUDA que el motor no usa)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY engine/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && python -m spacy download es_core_news_sm

WORKDIR /app/engine
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
