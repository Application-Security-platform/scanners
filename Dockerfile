# Use Python 3.12 slim as base image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y git librdkafka-dev gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy consumer files
COPY consumer/consumer.py .
COPY consumer/scanner_config.py .
COPY consumer/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV KAFKA_BOOTSTRAP_SERVERS=kafka-service.default.svc.cluster.local:9092
ENV KUBECONFIG=/app/.kube/config

# Create .kube directory
RUN mkdir -p /app/.kube

# Run the consumer
CMD ["python", "consumer.py"]