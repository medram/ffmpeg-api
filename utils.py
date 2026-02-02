import boto3


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
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

        # Try to list objects in the bucket
        s3_client.head_bucket(Bucket=s3_bucket)
        print(f"✓ S3 connection successful! Bucket '{s3_bucket}' is accessible.")
        return True
    except Exception as e:
        print(f"✗ S3 connection failed: {str(e)}", file=sys.stderr)
        return False
