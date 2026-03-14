FROM python:3.11-slim

WORKDIR /app

# Install dependencies, including debugging tools
RUN apt-get update && apt-get install -y \
  netcat-openbsd \
  curl \
  iproute2 \
  procps \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements_ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_ml.txt

# Copy app source
COPY . .

# Set entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# Expose port
EXPOSE 8080
