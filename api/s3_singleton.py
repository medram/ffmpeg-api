import os
from typing import Optional

import boto3
from botocore.client import Config


class S3ClientSingleton:
    _client: Optional[boto3.client] | None = None  # noqa # type: ignore
    _config: dict | None = None

    @classmethod
    def configure(
        cls,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "",
        s3_url: str | None = None,
    ):
        client_kwargs = {
            "service_name": "s3",
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "region_name": aws_region,
        }
        if s3_url is None:
            s3_url = os.environ.get("S3_ENDPOINT_URL")
        if s3_url:
            client_kwargs["endpoint_url"] = s3_url
        # Debug prints for troubleshooting
        # print(
        #     f"[S3 DEBUG] Configuring S3 client with endpoint: {client_kwargs.get('endpoint_url')} and region: {aws_region}"
        # )
        # print(f"[S3 DEBUG] Using bucket: {os.environ.get('S3_BUCKET')}")

        cls._config = client_kwargs
        cls._client = boto3.client(
            **client_kwargs,
            config=Config(
                signature_version="s3v4",  # Usually needed for path-style
            ),
        )

    @classmethod
    def get_client(cls):
        if cls._client is None:
            raise RuntimeError(
                "S3 client not configured. Call S3ClientSingleton.configure() first."
            )
        return cls._client
