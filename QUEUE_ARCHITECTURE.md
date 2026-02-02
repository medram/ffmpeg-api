# Queue-Based Architecture Guide

## Overview

The FFmpeg API now uses a **task queue with background workers** instead of synchronous execution. Tasks are automatically processed in the background, allowing for:

- **Non-blocking API responses** - Register a task and get instant response
- **Asynchronous processing** - Multiple workers process tasks in parallel
- **Scalability** - Add more workers to handle more tasks
- **Reliability** - Failed tasks remain in the system for inspection
- **Decoupling** - API and workers can run separately

## How It Works

### 1. Task Registration Flow

```
Client → POST /ffmpeg/register → Task Created → Task Enqueued → Immediate Response
                                                       ↓
                                              Background Worker
                                                 Picks up task
                                                      ↓
                                              Execute FFmpeg
                                                      ↓
                                              Upload to S3
```

### 2. Architecture Components

#### Task Queue (`api/task_queue.py`)

- In-memory async queue backed by `asyncio.Queue`
- Holds pending tasks waiting for processing
- Publishes events when tasks complete/fail
- Thread-safe and async-safe

#### Task Worker (`api/task_worker.py`)

- Processes tasks from the queue one at a time
- Downloads input files
- Executes FFmpeg command
- Uploads output to S3
- Handles errors gracefully
- Publishes status events

#### API Router (`api/ffmpeg_router.py`)

- **POST /ffmpeg/register** - Enqueue task immediately
- **GET /ffmpeg/status/{task_id}** - Check task status
- **GET /ffmpeg/queue/size** - Check queue size

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with S3 credentials
```

### 2. Start API with Embedded Workers

The API server automatically starts background workers:

```bash
# Starts API + 2 workers (default)
docker-compose up -d
```

Or locally:

```bash
source .venv/bin/activate
python -m uvicorn main:main --host 0.0.0.0 --port 8000
```

### 3. Register a Task

```bash
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "command": "-i input.mp4 output.mp4",
    "input_files": {"input.mp4": "https://example.com/video.mp4"},
    "output_filename": "output.mp4"
  }'

# Response:
# {
#   "task_id": "abc-123-def",
#   "status": "pending",
#   "output_url": null,
#   "error_message": null
# }
```

### 4. Check Task Status

```bash
curl http://localhost:8000/ffmpeg/status/abc-123-def

# While processing:
# {"task_id": "abc-123-def", "status": "running", ...}

# When complete:
# {
#   "task_id": "abc-123-def",
#   "status": "completed",
#   "output_url": "s3://bucket/ffmpeg-outputs/abc-123-def/output.mp4",
#   "error_message": null
# }
```

## Configuration

### Number of Workers

Control how many parallel tasks are processed:

```bash
# In .env file
NUM_WORKERS=4

# Or when starting API
python -m uvicorn main:main --env-file .env

# Or with Docker Compose, edit docker-compose.yml:
environment:
  NUM_WORKERS: 4
```

### Worker Configuration

```bash
# In .env file
S3_BUCKET=my-bucket
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1
NUM_WORKERS=2
```

## Running Workers Separately

For distributed processing, you can run workers in separate containers/servers:

### Standalone Worker Process

```bash
# Terminal 1: Start API (no workers)
python -m uvicorn main:main --host 0.0.0.0 --port 8000

# Terminal 2+: Start workers separately
NUM_WORKERS=2 python -m worker --num-workers 2

# Or with logging
LOG_LEVEL=DEBUG python -m worker --num-workers 2
```

### Docker Compose with Separate Workers

Create `docker-compose.workers.yml`:

```yaml
version: "3.9"

services:
  ffmpeg-api:
    build: .
    container_name: ffmpeg-api
    ports:
      - "8000:8000"
    environment:
      NUM_WORKERS: 0 # Don't start workers in API
      S3_BUCKET: ${S3_BUCKET}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    restart: unless-stopped

  worker-1:
    build: .
    container_name: ffmpeg-worker-1
    command: python -m worker --num-workers 1
    environment:
      S3_BUCKET: ${S3_BUCKET}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - ffmpeg-api
    restart: unless-stopped

  worker-2:
    build: .
    container_name: ffmpeg-worker-2
    command: python -m worker --num-workers 1
    environment:
      S3_BUCKET: ${S3_BUCKET}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - ffmpeg-api
    restart: unless-stopped
```

Run with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.workers.yml up -d
```

## Task Lifecycle

```
PENDING  → (Dequeued by worker)
RUNNING  → (FFmpeg executing)
COMPLETED → (Output uploaded to S3)
  or
FAILED   → (Error occurred)
```

### Status Transitions

- **PENDING**: Initial state after registration
- **RUNNING**: Worker picked up task and is processing
- **COMPLETED**: Task finished successfully, output available at `output_url`
- **FAILED**: Task failed, error details in `error_message`

## Monitoring

### Queue Size

Check how many tasks are pending:

```bash
curl http://localhost:8000/ffmpeg/queue/size
# {"queue_size": 3}
```

### Worker Logs

View worker activity:

```bash
# Docker Compose
docker-compose logs -f ffmpeg-api

# Standalone worker
LOG_LEVEL=DEBUG python -m worker
```

### Task Status

Poll task status to track progress:

```bash
while true; do
  curl -s http://localhost:8000/ffmpeg/status/task-id | jq .status
  sleep 2
done
```

## Performance Tuning

### Optimal Worker Count

```
Number of Workers = (CPU Cores / 2) to CPU Cores

Examples:
- 2-core system: 1-2 workers
- 4-core system: 2-4 workers
- 8-core system: 4-8 workers
```

### Memory per Worker

Each worker processes one task at a time. Memory requirements depend on:

- **Input file size** (downloaded to temp)
- **Output file size** (uploaded from temp)
- **FFmpeg overhead** (~200MB base)

Estimate: 500MB - 2GB per worker

### Docker Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: "2"
      memory: 2G
    reservations:
      cpus: "1"
      memory: 1G
```

## Advanced Features

### Event Subscriptions

Listen to task events:

```python
from api.task_queue import task_queue, TaskEvent

async def on_task_completed(task):
    print(f"Task {task.task_id} completed: {task.output_url}")

task_queue.subscribe(TaskEvent.TASK_COMPLETED, on_task_completed)
```

### Future Enhancements

The current queue-based system can be extended with:

1. **Redis Queue** - Replace in-memory queue with Redis for persistence
2. **RabbitMQ/Celery** - Enterprise message broker integration
3. **Database Persistence** - Store task history in PostgreSQL
4. **Metrics Collection** - Track processing times, success rates
5. **Webhooks** - Notify clients when tasks complete
6. **Priority Queue** - Process important tasks first
7. **Rate Limiting** - Limit concurrent tasks per user

## Troubleshooting

### Tasks Not Processing

1. Check if workers are running:

   ```bash
   docker-compose ps
   docker-compose logs ffmpeg-api
   ```

2. Verify NUM_WORKERS is > 0:

   ```bash
   docker-compose exec ffmpeg-api env | grep NUM_WORKERS
   ```

3. Check queue size:
   ```bash
   curl http://localhost:8000/ffmpeg/queue/size
   ```

### Worker Crashes

Check logs for errors:

```bash
docker-compose logs -f ffmpeg-api
# or
LOG_LEVEL=DEBUG python -m worker
```

### Memory Issues

- Reduce NUM_WORKERS
- Increase container memory limits
- Check input file sizes

### S3 Upload Failures

Verify credentials:

```bash
docker-compose exec ffmpeg-api python -c \
  "import boto3; s3 = boto3.client('s3'); print(s3.list_buckets())"
```

## Comparison: Sync vs Queue-Based

### Synchronous (Old)

```
POST /execute/{task_id}  ← Client waits
    ↓
Process task
    ↓
Return response  → Client gets result
```

**Issues:**

- Client waits for full processing (minutes)
- Requests timeout on long tasks
- Cannot process multiple tasks
- API becomes unresponsive

### Queue-Based (New)

```
POST /register  ← Client gets response immediately
    ↓
Task enqueued
    ↓
GET /status     ← Client polls for progress
    ↓
Task processed in background by workers
    ↓
Result ready when complete
```

**Benefits:**

- Instant response to client
- API never blocks
- Multiple parallel tasks
- Scalable to multiple workers/servers
- Better resource utilization

## Example: Batch Processing

```bash
#!/bin/bash

# Register 10 tasks
for i in {1..10}; do
  TASK_ID=$(curl -s -X POST http://localhost:8000/ffmpeg/register \
    -H "Content-Type: application/json" \
    -d "{
      \"command\": \"-i input$i.mp4 output$i.mp4\",
      \"input_files\": {\"input$i.mp4\": \"https://example.com/video$i.mp4\"},
      \"output_filename\": \"output$i.mp4\"
    }" | jq -r .task_id)

  echo "Task $i: $TASK_ID"
done

# Monitor all tasks
while true; do
  TOTAL=$(curl -s http://localhost:8000/ffmpeg/queue/size | jq .queue_size)
  echo "Tasks in queue: $TOTAL"
  sleep 5
done
```

---

**Architecture: Complete task queue-based system with background workers**
