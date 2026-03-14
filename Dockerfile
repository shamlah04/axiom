FROM python:3.11-slim

WORKDIR /app

# Install dependencies (including netcat for DB readiness checks)
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements_ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_ml.txt

# Copy app source
COPY . .

# Set entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Expose port (metadata for some proxies, though Railway uses $PORT)
EXPOSE 8080
