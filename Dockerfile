FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements_ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_ml.txt

# Copy app source
COPY . .

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
