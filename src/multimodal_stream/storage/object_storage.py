from typing import Protocol


class ObjectStorage(Protocol):
    def put_object(
        self,
        bucket: str,
        object_key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        ...

    def get_object(self, bucket: str, object_key: str) -> bytes:
        ...
