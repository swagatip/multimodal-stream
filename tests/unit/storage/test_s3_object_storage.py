import io
import os
import unittest
from unittest.mock import MagicMock, patch

from multimodal_stream.storage.s3_object_storage import S3ObjectStorage


class S3ObjectStorageTests(unittest.TestCase):
    @patch("multimodal_stream.storage.s3_object_storage.boto3.client")
    def test_configures_s3_client_for_s3_compatible_storage(
        self, client_factory: MagicMock
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "OBJECT_STORAGE_ENDPOINT_URL": "http://localhost:8333",
                "AWS_DEFAULT_REGION": "us-east-1",
            },
        ):
            S3ObjectStorage()

        client_factory.assert_called_once()
        args, kwargs = client_factory.call_args
        self.assertEqual(args, ("s3",))
        self.assertEqual(kwargs["endpoint_url"], "http://localhost:8333")
        self.assertEqual(kwargs["region_name"], "us-east-1")
        self.assertEqual(kwargs["config"].s3, {"addressing_style": "path"})

    @patch("multimodal_stream.storage.s3_object_storage.boto3.client")
    def test_put_object_uploads_bytes_and_content_type(
        self, client_factory: MagicMock
    ) -> None:
        storage = S3ObjectStorage(endpoint_url="http://localhost:8333")

        storage.put_object(
            "video-chunks",
            "videos/example/000000",
            b"chunk-data",
            "video/mp4",
        )

        client_factory.return_value.put_object.assert_called_once_with(
            Bucket="video-chunks",
            Key="videos/example/000000",
            Body=b"chunk-data",
            ContentType="video/mp4",
        )

    @patch("multimodal_stream.storage.s3_object_storage.boto3.client")
    def test_get_object_returns_bytes_and_closes_response_body(
        self, client_factory: MagicMock
    ) -> None:
        body = io.BytesIO(b"chunk-data")
        client_factory.return_value.get_object.return_value = {"Body": body}
        storage = S3ObjectStorage(endpoint_url="http://localhost:8333")

        result = storage.get_object("video-chunks", "videos/example/000000")

        self.assertEqual(result, b"chunk-data")
        self.assertTrue(body.closed)
        client_factory.return_value.get_object.assert_called_once_with(
            Bucket="video-chunks",
            Key="videos/example/000000",
        )
