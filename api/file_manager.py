import os
import tempfile

import httpx


class FileManager:
    """Handles file download and S3 upload operations."""

    def __init__(
        self,
        s3_bucket: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1",
        s3_url: str | None = None,
    ):
        from .s3_singleton import S3ClientSingleton

        self.s3_bucket = s3_bucket
        self.temp_dir = tempfile.mkdtemp()
        S3ClientSingleton.configure(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
            s3_url=s3_url,
        )
        self.s3_client = S3ClientSingleton.get_client()

    async def download_file(self, url: str, filename: str) -> str:
        """Download a file from URL and save it locally.

        Args:
            url: URL of the file to download
            filename: Local filename to save as

        Returns:
            Path to the downloaded file
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            file_path = os.path.join(self.temp_dir, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)

            return file_path

    async def download_files(self, input_files: dict[str, str]) -> dict[str, str]:
        """Download multiple files and log file existence and size after download."""
        import logging

        local_paths = {}
        logger = logging.getLogger(__name__)
        logger.info(f"Using temp directory: {self.temp_dir}")
        for filename, url in input_files.items():
            local_path = await self.download_file(url, filename)
            local_paths[filename] = local_path
            # Log file existence and size
            if os.path.exists(local_path):
                size = os.path.getsize(local_path)
                logger.info(f"Downloaded {filename} to {local_path} (size: {size} bytes)")
            else:
                logger.error(f"File {local_path} does not exist after download!")
        return local_paths

    def upload_to_s3(self, file_path: str, s3_key: str) -> str:
        """Upload a file to S3 bucket and return a 7-day pre-signed HTTP URL."""
        self.s3_client.upload_file(
            file_path,
            self.s3_bucket,
            s3_key,
        )

        # Generate a pre-signed HTTP URL valid for 7 days (604800 seconds)
        presigned_url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.s3_bucket, "Key": s3_key},
            ExpiresIn=604800,  # 7 days in seconds
        )
        return presigned_url

    def cleanup(self) -> None:
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def get_temp_file_path(self, filename: str) -> str:
        """Get path for a file in the temp directory."""
        return os.path.join(self.temp_dir, filename)
