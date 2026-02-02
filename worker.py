#!/usr/bin/env python
"""
Standalone worker script for processing FFmpeg tasks.

This can be run separately from the API server for distributed processing.

Usage:
    python -m worker [--num-workers NUM] [--log-level LEVEL]

Environment variables:
    NUM_WORKERS: Number of concurrent workers (default: 2)
    S3_BUCKET: S3 bucket name
    AWS_ACCESS_KEY_ID: AWS access key
    AWS_SECRET_ACCESS_KEY: AWS secret key
    AWS_REGION: AWS region (default: us-east-1)
    LOG_LEVEL: Logging level (default: INFO)
"""

import asyncio
import logging
import os
import sys
from argparse import ArgumentParser

from api.task_worker import run_workers

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run the task workers."""
    parser = ArgumentParser(description="FFmpeg API Task Worker")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=int(os.getenv("NUM_WORKERS", "2")),
        help="Number of concurrent workers",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level",
    )

    args = parser.parse_args()

    # Update logging level
    logging.getLogger().setLevel(args.log_level)

    # Get configuration
    num_workers = args.num_workers
    s3_bucket = os.getenv("S3_BUCKET", "ffmpeg-output")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    logger.info(f"Starting {num_workers} worker(s)")
    logger.info(f"S3 Bucket: {s3_bucket}")

    try:
        # Run workers
        await run_workers(
            num_workers=num_workers,
            s3_bucket=s3_bucket,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
    except KeyboardInterrupt:
        logger.info("Shutting down workers...")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
