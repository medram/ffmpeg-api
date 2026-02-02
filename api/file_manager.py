import os
import tempfile

import boto3
import httpx


class FileManager:
    """Handles file download and S3 upload operations."""

    def __init__(
        self,
        s3_bucket: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "us-east-1",
    ):
        self.s3_bucket = s3_bucket
        self.temp_dir = tempfile.mkdtemp()
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

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
        """Download multiple files.

        Args:
            input_files: Dict mapping local filenames to URLs

        Returns:
            Dict mapping filenames to local paths
        """
        local_paths = {}
        for filename, url in input_files.items():
            local_path = await self.download_file(url, filename)
            local_paths[filename] = local_path
        return local_paths

    def upload_to_s3(self, file_path: str, s3_key: str) -> str:
        """Upload a file to S3 bucket.

        Args:
            file_path: Local path to the file to upload
            s3_key: S3 key (path in bucket)

        Returns:
            S3 URL of the uploaded file
        """
        self.s3_client.upload_file(
            file_path,
            self.s3_bucket,
            s3_key,
        )

        # Generate S3 URL
        s3_url = f"s3://{self.s3_bucket}/{s3_key}"
        return s3_url

    def cleanup(self) -> None:
        """Clean up temporary files."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def get_temp_file_path(self, filename: str) -> str:
        """Get path for a file in the temp directory."""
        return os.path.join(self.temp_dir, filename)
