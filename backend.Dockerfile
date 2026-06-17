FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required for pgvector and building Python packages
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy your dependency file
COPY pyproject.toml ./

# ADDED: watchdog for Celery live-reloading!
RUN pip install --default-timeout=1000 --no-cache-dir . uvicorn fastapi pydantic watchdog

# Copy the rest of the backend code
# (Note: In dev, your docker-compose volumes will override these, which is perfect)
COPY src/ ./src/
COPY dataset/ ./dataset/
COPY models/ ./models/

# Expose the API port
EXPOSE 8000

# Start the FastAPI server (uvicorn --reload handles the API hot-reloading)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]