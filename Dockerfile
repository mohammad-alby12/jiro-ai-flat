FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py config.py database.py db_models.py schemas.py documents.py inference.py model_manager.py ./
RUN mkdir -p ./static
COPY index.html app.js style.css ./static/
RUN mkdir -p /app/data/uploads /app/models
EXPOSE 8000
# Railway injects PORT at runtime; fall back to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
