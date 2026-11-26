import os

import boto3
from botocore.config import Config


class S3ObjectStorage:
    def __init__(self, endpoint_url: str | None = None) -> None:
        endpoint_url = endpoint_url or os.getenv("OBJECT_STORAGE_ENDPOINT_URL")
        client_options: dict[str, object] = {
            "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        }
        if endpoint_url:
            client_options["endpoint_url"] = endpoint_url
            client_options["config"] = Config(
                s3={"addressing_style": "path"},
            )

        self._client = boto3.client("s3", **client_options)

    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        self._client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )

    def get_object(self, bucket: str, object_key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=object_key)
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()
