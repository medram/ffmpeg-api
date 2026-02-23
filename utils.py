from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.file_manager import FileManager


def check_s3_connection(
    s3_bucket: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    aws_region: str,
) -> bool:
    """Check S3 connection by listing buckets.

    Args:
        s3_bucket: S3 bucket name
        aws_access_key_id: AWS access key ID
        aws_secret_access_key: AWS secret access key
        aws_region: AWS region

    Returns:
        True if connection is successful, False otherwise
    """
    try:
        from api.s3_singleton import S3ClientSingleton

        S3ClientSingleton.configure(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        s3_client = S3ClientSingleton.get_client()
        s3_client.head_bucket(Bucket=s3_bucket)
        print(f"✓ S3 connection successful! Bucket '{s3_bucket}' is accessible.")
        return True
    except Exception as e:
        print(f"✗ S3 connection failed: {str(e)}", file=sys.stderr)
        return False


def get_file_manager() -> FileManager:
    """Get a configured FileManager instance."""
    from api.file_manager import FileManager

    return FileManager(
        s3_bucket=os.getenv("S3_BUCKET", "ffmpeg-output"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        s3_url=os.getenv("S3_ENDPOINT_URL", None),
    )
