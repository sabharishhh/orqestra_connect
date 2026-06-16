
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pgvector and building Python packages
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Copy your dependency file
COPY pyproject.toml ./

# Install dependencies 
RUN pip install --no-cache-dir . uvicorn fastapi pydantic

# Copy the rest of the backend code
COPY src/ ./src/
COPY dataset/ ./dataset/
COPY models/ ./models/

# Expose the API port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]