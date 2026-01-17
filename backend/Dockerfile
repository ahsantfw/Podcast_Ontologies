FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt /tmp/backend-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt && \
    pip install --no-cache-dir \
    neo4j \
    qdrant-client \
    openai \
    python-dotenv \
    langchain \
    langchain-community \
    langchain-openai \
    numpy \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    pydantic \
    jinja2 \
    aiofiles \
    sqlalchemy

# Copy application code
COPY . /app

# Set Python path
ENV PYTHONPATH=/app
ENV PORT=8080

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/api/health')" || exit 1

# Run application
CMD exec uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 1

