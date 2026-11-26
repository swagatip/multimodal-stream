import logging
import os
import tempfile
import unittest
from logging.config import fileConfig
from pathlib import Path
from pprint import pformat
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from multimodal_stream.storage.object_storage import ObjectStorage
from multimodal_stream.storage.s3_object_storage import S3ObjectStorage
from multimodal_stream.video.video_chunker import VideoChunker

fileConfig(
    Path(__file__).parent.parent / "unit" / "logging.ini",
    disable_existing_loggers=False,
)

logger = logging.getLogger("multimodal_stream.integration.video_object_storage")


class VideoObjectStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        endpoint_url = os.getenv("OBJECT_STORAGE_ENDPOINT_URL")
        if not endpoint_url:
            raise unittest.SkipTest(
                "Set OBJECT_STORAGE_ENDPOINT_URL to run SeaweedFS integration tests."
            )

        cls.bucket = os.getenv("OBJECT_STORAGE_TEST_BUCKET", "video-chunks")
        cls.storage: ObjectStorage = S3ObjectStorage(endpoint_url=endpoint_url)
        cls.s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        )

        try:
            cls.s3_client.create_bucket(Bucket=cls.bucket)
        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code")
            if error_code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                raise
            cls.s3_client.head_bucket(Bucket=cls.bucket)

    def test_video_chunks_round_trip_through_object_storage(self) -> None:
        original_data = bytes(range(256)) * 2
        video_id = uuid4().hex
        stored_keys: list[str] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "sample.bin"
            video_path.write_bytes(original_data)

            chunks = list(VideoChunker().create_chunks(video_path, chunk_size=64))
            try:
                for chunk in chunks:
                    object_key = (
                        f"integration-tests/{video_id}/"
                        f"chunks/{chunk.chunk_index:06d}"
                    )
                    self.storage.put_object(
                        self.bucket,
                        object_key,
                        chunk.data,
                    )
                    stored_keys.append(object_key)
                    self.assertEqual(
                        self.storage.get_object(self.bucket, object_key),
                        chunk.data,
                    )

                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=f"integration-tests/{video_id}/",
                )
                uploaded_objects = [
                    (item["Key"], item["Size"])
                    for item in response.get("Contents", [])
                ]
                logger.info(
                    "S3 bucket %s objects for video %s after upload "
                    "(key, size_bytes):\n%s",
                    self.bucket,
                    video_id,
                    pformat(uploaded_objects, indent=2),
                )

                reconstructed_data = b"".join(
                    self.storage.get_object(
                        self.bucket,
                        f"integration-tests/{video_id}/chunks/"
                        f"{chunk.chunk_index:06d}",
                    )
                    for chunk in chunks
                )
                self.assertEqual(reconstructed_data, original_data)
            finally:
                for object_key in stored_keys:
                    self.s3_client.delete_object(
                        Bucket=self.bucket,
                        Key=object_key,
                    )
