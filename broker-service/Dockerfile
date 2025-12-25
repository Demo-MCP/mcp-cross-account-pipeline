FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install fastapi uvicorn[standard] boto3 requests

# Copy broker app
COPY broker.py ./app.py

# Run broker as HTTP service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
