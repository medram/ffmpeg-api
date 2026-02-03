# ffmpeg-api

A RESTful API for executing FFmpeg commands with asynchronous task management, built with FastAPI.

## Features

- **Task Registration**: Register FFmpeg tasks with commands, input file URLs, and output filename
- **Asynchronous Execution**: Execute tasks asynchronously with task ID tracking
- **Status Checking**: Poll task status to check if execution is complete
- **File Management**: Automatically download input files from URLs and upload outputs to S3
- **S3 Integration**: Output files are automatically uploaded to AWS S3 and downloadable HTTP links (pre-signed, valid for 7 days) are returned

## Requirements

- Python 3.12+
- FFmpeg installed on the system
- AWS S3 credentials for upload functionality

## Installation

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## Configuration

Set the following environment variables:

```bash
export S3_BUCKET="your-s3-bucket-name"
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export AWS_REGION="us-east-1"  # Optional, defaults to us-east-1
```

## Running the Server

```bash
python -m main
```

The API will be available at `http://localhost:8000`

- API documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## API Endpoints

### 1. Register Task

**POST** `/ffmpeg/register`

Register a new FFmpeg task and get a task ID.

**Request Body:**

```json
{
  "ffmpeg_command": "-i in_1 -c:v libx264 -crf 23 out_1",
  "input_files": {
    "in_1": "https://example.com/video.mp4"
  },
  "output_files": {
    "out_1": "output.mp4"
  }
}
```

**Response:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "output_urls": null,
  "error_message": null
}
```

### 3. Check Task Status

**GET** `/ffmpeg/status/{task_id}`

Check the status of a task without executing it. If completed, returns a downloadable HTTP link (pre-signed, valid for 7 days).

**Path Parameters:**

- `task_id` (string, required): The task ID

**Response:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "output_urls": {
    "out_1": "https://your-bucket.s3.amazonaws.com/ffmpeg-outputs/550e8400-e29b-41d4-a716-446655440000/output.mp4?X-Amz-Expires=604800&..."
  },
  "error_message": null
}
```

### 4. Health Check

**GET** `/health`

Check API health status.

**Response:**

```json
{
  "status": "ok"
}
```

**GET** `/ffmpeg/health`

Check FFmpeg availability on the system.

**Response:**

```json
{
  "status": "ok",
  "ffmpeg_installed": "yes"
}
```

## Task Statuses

- `pending`: Task has been registered but not yet executed
- `running`: Task is currently being executed
- `completed`: Task has been successfully completed, output_url contains the S3 URL
- `failed`: Task execution failed, error_message contains details

## Example Workflow

```bash

# 1. Register a task
curl -X POST http://localhost:8000/ffmpeg/register \
  -H "Content-Type: application/json" \
  -d '{
    "ffmpeg_command": "-i in_1 -vf scale=1280:720 out_1",
    "input_files": {"in_1": "https://example.com/video.mp4"},
    "output_files": {"out_1": "output.mp4"}
  }'

# Response: {"task_id": "abc-123", "status": "pending", ...}




# 3. Or check status without executing
curl http://localhost:8000/ffmpeg/status/abc-123

# Response: {"task_id": "abc-123", "status": "completed",
#           "output_urls": {"out_1": "https://bucket.s3.amazonaws.com/ffmpeg-outputs/abc-123/output.mp4?X-Amz-Expires=604800&..."}, ...}
```

## Notes

- Input files must be provided as URLs and will be downloaded to a temporary directory
- The FFmpeg command should not include the `ffmpeg` prefix
- Input filenames in the command should match the keys in `input_files` dictionary
- Output files are automatically uploaded to S3 with a key pattern: `ffmpeg-outputs/{task_id}/{output_filename}`
- Output URLs returned by the API are downloadable HTTP links (pre-signed, valid for 7 days). These links expire after 7 days for security.
- Temporary files are cleaned up after task completion or failure
- The API uses in-memory task storage; tasks are lost on server restart
