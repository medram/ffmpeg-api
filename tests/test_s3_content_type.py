import os
import tempfile
import pytest
from api.file_manager import FileManager

@pytest.fixture
def s3_file_manager(monkeypatch):
    # Use dummy credentials and bucket for testing
    fm = FileManager(
        s3_bucket="test-bucket",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        aws_region="us-east-1",
        s3_url=os.environ.get("S3_ENDPOINT_URL"),
    )
    return fm

def test_upload_sets_content_type(s3_file_manager):
    # Create a temporary file with a known extension
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"hello world")
        tmp_path = tmp.name
    s3_key = "test-folder/test-file.txt"
    # Upload file
    url = s3_file_manager.upload_to_s3(tmp_path, s3_key)
    # Fetch metadata from S3 to verify content-type
    s3 = s3_file_manager.s3_client
    head = s3.head_object(Bucket=s3_file_manager.s3_bucket, Key=s3_key)
    assert head["ContentType"] == "text/plain"
    os.remove(tmp_path)
