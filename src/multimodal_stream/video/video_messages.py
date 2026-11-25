from typing import Literal, TypedDict


class VideoChunkMessage(TypedDict):
    schema_version: Literal[1]
    event_type: Literal["video.chunk"]
    event_id: str
    video_id: str
    created_at: str
    chunk_index: int
    chunk_count: int
    bucket: str
    object_key: str
    offset_bytes: int
    size_bytes: int
    sha256: str


class VideoCompletedMessage(TypedDict):
    schema_version: Literal[1]
    event_type: Literal["video.completed"]
    event_id: str
    video_id: str
    created_at: str
    file_name: str
    content_type: str
    total_size_bytes: int
    sha256: str
    chunk_count: int
