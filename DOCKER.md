# Docker Deployment Guide

## Overview

The FFmpeg API includes complete Docker support for easy containerization and deployment.

## Files Included

- **Dockerfile** - Multi-stage build for optimized image size
- **docker-compose.yml** - Complete service configuration
- **.dockerignore** - Excludes unnecessary files from build context

## Quick Start with Docker

### 1. Build the Docker Image

```bash
# Build image
docker build -t ffmpeg-api:latest .

# Or with compose
docker-compose build
```

### 2. Run with Docker Compose (Recommended)

Create a `.env` file with your S3 credentials:

```bash
cat > .env << EOF
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
EOF
```

Then start the container:

```bash
docker-compose up -d
```

### 3. Verify the Service

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f ffmpeg-api

# Test the API
curl http://localhost:8000/health
```

## Docker Commands

### Build Image

```bash
# Build image
docker build -t ffmpeg-api:latest .

# Build with specific tag
docker build -t ffmpeg-api:v1.0 .

# Build without cache
docker build --no-cache -t ffmpeg-api:latest .
```

### Run Container

```bash
# Basic run with environment variables
docker run -p 8000:8000 \
  -e S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=key \
  -e AWS_SECRET_ACCESS_KEY=secret \
  ffmpeg-api:latest

# Run with .env file
docker run -p 8000:8000 --env-file .env ffmpeg-api:latest

# Run in background
docker run -d -p 8000:8000 --env-file .env --name ffmpeg-api ffmpeg-api:latest

# Run with volume mount for logs
docker run -d -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  --name ffmpeg-api \
  ffmpeg-api:latest
```

### Docker Compose Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f ffmpeg-api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart services
docker-compose restart

# Build and start
docker-compose up -d --build

# Execute command in container
docker-compose exec ffmpeg-api bash
```

## Environment Configuration

### Using .env File

Create `.env` file in project root:

```env
S3_BUCKET=your-bucket-name
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
```

Then run:

```bash
docker-compose up -d
```

### Using Environment Variables

```bash
docker run -d \
  -p 8000:8000 \
  -e S3_BUCKET=my-bucket \
  -e AWS_ACCESS_KEY_ID=key \
  -e AWS_SECRET_ACCESS_KEY=secret \
  -e AWS_REGION=us-west-2 \
  ffmpeg-api:latest
```

### Using Docker Compose Override

Create `docker-compose.override.yml`:

```yaml
version: "3.9"

services:
  ffmpeg-api:
    environment:
      S3_BUCKET: my-bucket
      AWS_ACCESS_KEY_ID: my-key
      AWS_SECRET_ACCESS_KEY: my-secret
```

## Port Mapping

The API runs on port 8000 inside the container. Map it as needed:

```bash
# Map to same port
docker run -p 8000:8000 ffmpeg-api:latest

# Map to different port
docker run -p 3000:8000 ffmpeg-api:latest

# Access via http://localhost:3000/docs
```

## Using the API in Docker

Once running, access the API:

```bash
# Health check
curl http://localhost:8000/health

# API documentation
curl http://localhost:8000/docs
curl http://localhost:8000/redoc

# Register task
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 output.mp4",
    "input_files": {"input.mp4": "https://example.com/video.mp4"},
    "output_filename": "output.mp4"
  }'
```

## Health Checks

The container includes a health check that:

- Runs every 30 seconds
- Times out after 10 seconds
- Requires 3 consecutive failures to mark unhealthy
- Has a 5-second startup grace period

Check health status:

```bash
docker ps  # Shows (healthy) or (unhealthy)
docker inspect --format='{{.State.Health.Status}}' ffmpeg-api
```

## Resource Limits

Configure resource limits in docker-compose.yml:

```yaml
services:
  ffmpeg-api:
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
        reservations:
          cpus: "1"
          memory: 1G
```

Or with docker run:

```bash
docker run -d \
  --cpus 2 \
  --memory 2g \
  -p 8000:8000 \
  ffmpeg-api:latest
```

## Logging

View container logs:

```bash
# View all logs
docker logs ffmpeg-api

# Follow logs
docker logs -f ffmpeg-api

# Last 100 lines
docker logs --tail 100 ffmpeg-api

# With timestamps
docker logs -f --timestamps ffmpeg-api
```

Docker Compose logs:

```bash
# View service logs
docker-compose logs ffmpeg-api

# Follow logs
docker-compose logs -f ffmpeg-api

# Last 100 lines
docker-compose logs --tail 100 ffmpeg-api
```

## Persistent Storage

### Mount Volumes

```bash
# Mount logs directory
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  ffmpeg-api:latest
```

Docker Compose:

```yaml
services:
  ffmpeg-api:
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
```

## Debugging

### Enter Container Shell

```bash
# Docker
docker exec -it ffmpeg-api bash

# Docker Compose
docker-compose exec ffmpeg-api bash
```

### Check FFmpeg Installation

```bash
docker exec ffmpeg-api ffmpeg -version
```

### Verify Python Environment

```bash
docker exec ffmpeg-api python --version
docker exec ffmpeg-api pip list
```

### Test API

```bash
docker exec ffmpeg-api curl http://localhost:8000/health
docker exec ffmpeg-api curl http://localhost:8000/ffmpeg/health
```

## Pushing to Registry

### Docker Hub

```bash
# Tag image
docker tag ffmpeg-api:latest your-username/ffmpeg-api:latest

# Login
docker login

# Push
docker push your-username/ffmpeg-api:latest

# Pull
docker pull your-username/ffmpeg-api:latest
```

### Private Registry

```bash
# Tag for private registry
docker tag ffmpeg-api:latest registry.example.com/ffmpeg-api:latest

# Push to private registry
docker push registry.example.com/ffmpeg-api:latest
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build image
        run: docker build -t ffmpeg-api:${{ github.sha }} .

      - name: Push to registry
        run: |
          docker tag ffmpeg-api:${{ github.sha }} your-registry/ffmpeg-api:latest
          docker push your-registry/ffmpeg-api:latest
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs ffmpeg-api

# Check for errors
docker inspect ffmpeg-api
```

### Permission Denied

```bash
# Run with sudo
sudo docker run -d -p 8000:8000 ffmpeg-api:latest

# Or add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Port Already in Use

```bash
# Change port mapping
docker run -d -p 3000:8000 ffmpeg-api:latest

# Kill existing container
docker stop ffmpeg-api
docker rm ffmpeg-api
```

### Out of Memory

```bash
# Increase memory limit
docker run -d --memory 4g -p 8000:8000 ffmpeg-api:latest

# Or in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
```

## Production Deployment

### Best Practices

1. **Use specific tags** - Avoid `latest` in production
2. **Set resource limits** - Define CPU and memory limits
3. **Enable health checks** - Already configured in Dockerfile
4. **Use environment files** - Keep secrets secure
5. **Enable logging** - Aggregate container logs
6. **Use restart policies** - Restart on failure

### Docker Compose Production

```yaml
services:
  ffmpeg-api:
    image: ffmpeg-api:v1.0
    restart: always
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 2G
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ffmpeg-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ffmpeg-api
  template:
    metadata:
      labels:
        app: ffmpeg-api
    spec:
      containers:
        - name: ffmpeg-api
          image: ffmpeg-api:v1.0
          ports:
            - containerPort: 8000
          env:
            - name: S3_BUCKET
              valueFrom:
                secretKeyRef:
                  name: ffmpeg-api-secrets
                  key: s3-bucket
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: ffmpeg-api-secrets
                  key: aws-access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: ffmpeg-api-secrets
                  key: aws-secret-key
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            limits:
              cpu: "2"
              memory: "2Gi"
            requests:
              cpu: "1"
              memory: "1Gi"
```

## Next Steps

1. Build the image: `docker-compose build`
2. Configure `.env` with your S3 credentials
3. Start the service: `docker-compose up -d`
4. Access the API: `http://localhost:8000/docs`
5. Monitor logs: `docker-compose logs -f`
