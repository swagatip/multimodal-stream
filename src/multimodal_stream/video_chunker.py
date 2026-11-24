import hashlib
import logging
import os
from pathlib import Path
from typing import BinaryIO, Iterator

from multimodal_stream.video_data_types import VideoChunk

logger = logging.getLogger(__name__)


class VideoChunker:
    DEFAULT_CHUNK_SIZE_BYTES = 64 * 1024

    def create_chunks(
        self,
        video_path: Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE_BYTES,
    ) -> Iterator[VideoChunk]:
        if not self._is_positive_integer(chunk_size):
            raise ValueError("chunk_size must be a positive integer.")

        with video_path.open("rb") as video_file:
            file_size = os.fstat(video_file.fileno()).st_size
            if file_size == 0:
                logger.warning(
                    "Video file %s is empty; no chunks were created.", video_path
                )
                return

            chunk_count = (file_size + chunk_size - 1) // chunk_size
            yield from self._iter_chunks(video_file, chunk_count, chunk_size)

    @staticmethod
    def _iter_chunks(
        video_file: BinaryIO,
        chunk_count: int,
        chunk_size: int,
    ) -> Iterator[VideoChunk]:
        for chunk_index in range(chunk_count):
            data = video_file.read(chunk_size)
            if not data:
                break

            chunk = VideoChunk(
                chunk_index=chunk_index,
                chunk_count=chunk_count,
                offset_bytes=chunk_index * chunk_size,
                data=data,
                sha256=hashlib.sha256(data).hexdigest(),
            )
            logger.info(
                "Created video chunk %d/%d (offset_bytes=%d, size_bytes=%d)",
                chunk.chunk_index,
                chunk.chunk_count,
                chunk.offset_bytes,
                chunk.size_bytes,
            )
            yield chunk

    @staticmethod
    def _is_positive_integer(value: object) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        )
