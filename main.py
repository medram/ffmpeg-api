import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api import api, run_workers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle events."""
    # Startup
    num_workers = int(os.getenv("NUM_WORKERS", "2"))
    s3_bucket = os.getenv("S3_BUCKET", "ffmpeg-output")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    await run_workers(
        num_workers=num_workers,
        s3_bucket=s3_bucket,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
    )

    yield

    # Shutdown (cleanup code here if needed)


def main() -> FastAPI:
    app = FastAPI(
        title="FFmpeg API",
        description="RESTful API for executing FFmpeg commands with background worker tasks",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    # Include FFmpeg router
    app.include_router(api, prefix="/ffmpeg", tags=["ffmpeg"])

    return app


if __name__ == "__main__":
    app = main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
