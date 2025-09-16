FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements from app subfolder and install
COPY "fruit-recommender - 4.0/fruit-recommender - 4.0/requirements.txt" /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# Copy application code (subfolder contains main.py, index.html, assets)
COPY "fruit-recommender - 4.0/fruit-recommender - 4.0/" /app/

EXPOSE 7860

CMD ["gunicorn", "-b", "0.0.0.0:${PORT}", "main:app"]


