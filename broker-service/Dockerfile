FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY agents/ ./agents/
COPY schemas.py ./schemas.py
COPY observability.py ./observability.py
COPY strands_app.py ./app.py

# Run Strands broker as HTTP service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
