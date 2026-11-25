import hashlib
import logging
import tempfile
from pathlib import Path
from typing import BinaryIO, Iterable, NamedTuple

from multimodal_stream.video_data_types import VideoChunk

logger = logging.getLogger(__name__)


class ChunkLayout(NamedTuple):
    offset_bytes: int
    size_bytes: int


class VideoAssembler:
    DEFAULT_CHUNK_SIZE_BYTES = 64 * 1024
    
    def stitch_chunks(
        self,
        chunks: Iterable[VideoChunk],
        output_path: Path,
        expected_size_bytes: int,
        expected_sha256: str,
        expected_chunk_count: int,
    ) -> Path:
        
        # Validate inputs
        if not self._is_non_negative_integer(expected_size_bytes):
            raise ValueError("expected_size_bytes must be a non-negative integer.")
        if not self._is_valid_sha256(expected_sha256):
            raise ValueError("expected_sha256 must be a 64-character hexadecimal digest.")
        if not self._is_non_negative_integer(expected_chunk_count):
            raise ValueError("expected_chunk_count must be a non-negative integer.")

        # initiate variables
        output_path = Path(output_path)
        staging_filepath: Path | None = None
        
        # chunk_metadata example, 130 byte data:
        # {
        #     0: ChunkLayout(offset_bytes=0, size_bytes=64),
        #     1: ChunkLayout(offset_bytes=64, size_bytes=64),
        #     2: ChunkLayout(offset_bytes=128, size_bytes=2),
        # }
        chunk_metadata: dict[int, ChunkLayout] = {}

        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b",
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as staging_file:
                staging_filepath = Path(staging_file.name)

                for chunk in chunks:
                    self._stitch_single_chunk(
                        chunk,
                        expected_size_bytes,
                        expected_chunk_count,
                        chunk_metadata,
                        staging_file,
                    )
                    self._update_chunk_metadata(chunk, chunk_metadata)

                self._verify_chunk_assembly(
                    expected_chunk_count,
                    expected_size_bytes,
                    chunk_metadata,
                )

                self._verify_staged_file_sha256(staging_file, expected_sha256)

            staging_filepath.replace(output_path)
            logger.info(
                "Assembled video: chunks=%d, size_bytes=%d, destination=%s",
                expected_chunk_count,
                expected_size_bytes,
                output_path,
            )
            return output_path
        finally:
            if staging_filepath is not None and staging_filepath.exists():
                staging_filepath.unlink()

    @staticmethod
    def _is_non_negative_integer(value: object) -> bool:
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
        )

    @staticmethod
    def _is_valid_sha256(value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdefABCDEF" for character in value)
        )

    def _stitch_single_chunk(
        self,
        chunk: VideoChunk,
        expected_size_bytes: int,
        expected_chunk_count: int,
        chunk_metadata: dict[int, ChunkLayout],
        staging_file: BinaryIO,
    ) -> None:
        self._validate_chunk_structure_or_raise(chunk)
        self._validate_chunk_for_assembly_or_raise(
            chunk=chunk,
            expected_size_bytes=expected_size_bytes,
            expected_chunk_count=expected_chunk_count,
            chunk_metadata=chunk_metadata,
        )

        # Write the data at the correct offset in the staging file.
        staging_file.seek(chunk.offset_bytes)
        staging_file.write(chunk.data)

    @staticmethod
    def _validate_chunk_structure_or_raise(chunk: VideoChunk) -> None:
        if not isinstance(chunk, VideoChunk):
            raise ValueError("Each item must be a VideoChunk.")
        if (
            not isinstance(chunk.chunk_count, int)
            or isinstance(chunk.chunk_count, bool)
            or chunk.chunk_count <= 0
        ):
            raise ValueError("chunk_count must be a positive integer.")
        if (
            not isinstance(chunk.chunk_index, int)
            or isinstance(chunk.chunk_index, bool)
            or not 0 <= chunk.chunk_index < chunk.chunk_count
        ):
            raise ValueError("chunk_index must be within the chunk count.")
        if (
            not isinstance(chunk.offset_bytes, int)
            or isinstance(chunk.offset_bytes, bool)
            or chunk.offset_bytes < 0
        ):
            raise ValueError("offset_bytes must be a non-negative integer.")
        if not isinstance(chunk.data, bytes) or not chunk.data:
            raise ValueError("Video chunk data must be non-empty bytes.")
        if not isinstance(chunk.sha256, str):
            raise ValueError("Video chunk sha256 must be a string.")

    @staticmethod
    def _validate_chunk_for_assembly_or_raise(
        chunk: VideoChunk,
        expected_size_bytes: int,
        expected_chunk_count: int,
        chunk_metadata: dict[int, ChunkLayout],
    ) -> None:
        if chunk.chunk_count != expected_chunk_count:
            raise ValueError(
                f"Video chunk {chunk.chunk_index} reports {chunk.chunk_count} chunks; "
                f"expected {expected_chunk_count}."
            )

        if chunk.chunk_index in chunk_metadata:
            raise ValueError(f"Duplicate video chunk index: {chunk.chunk_index}.")

        if chunk.offset_bytes + chunk.size_bytes > expected_size_bytes:
            raise ValueError(
                f"Video chunk {chunk.chunk_index} exceeds the expected file size."
            )

        actual_chunk_sha256 = hashlib.sha256(chunk.data).hexdigest()
        if actual_chunk_sha256 != chunk.sha256.lower():
            raise ValueError(f"Checksum mismatch for video chunk {chunk.chunk_index}.")

    @staticmethod
    def _update_chunk_metadata(
        chunk: VideoChunk,
        chunk_metadata: dict[int, ChunkLayout],
    ) -> None:
        chunk_metadata[chunk.chunk_index] = ChunkLayout(
            offset_bytes=chunk.offset_bytes,
            size_bytes=chunk.size_bytes,
        )

    def _verify_chunk_assembly(
        self,
        expected_chunk_count: int,
        expected_size_bytes: int,
        chunk_metadata: dict[int, ChunkLayout],
    ) -> None:
        if len(chunk_metadata) != expected_chunk_count:
            raise ValueError(
                f"Missing video chunks: received {len(chunk_metadata)} "
                f"of {expected_chunk_count}."
            )

        assembled_size_bytes = 0
        for chunk_index in range(expected_chunk_count):
            self._verify_chunk_offset(chunk_metadata, assembled_size_bytes, chunk_index)
            assembled_size_bytes += chunk_metadata[chunk_index].size_bytes

        if assembled_size_bytes != expected_size_bytes:
            raise ValueError(
                f"Assembled size mismatch: expected {expected_size_bytes}, "
                f"got {assembled_size_bytes}."
            )

    def _verify_chunk_offset(
        self,
        chunk_metadata: dict[int, ChunkLayout],
        assembled_size_bytes: int,
        chunk_index: int,
    ) -> None:
        if chunk_index not in chunk_metadata:
            raise ValueError(f"Missing video chunk index: {chunk_index}.")

        chunk_layout = chunk_metadata[chunk_index]
        if chunk_layout.offset_bytes != assembled_size_bytes:
            raise ValueError(
                f"Unexpected offset for video chunk {chunk_index}: "
                f"expected {assembled_size_bytes}, got {chunk_layout.offset_bytes}."
            )

    def _verify_staged_file_sha256(
        self,
        staging_file: BinaryIO,
        expected_sha256: str,
    ) -> None:
        staging_file.flush()
        staging_file.seek(0)
        assembled_sha256 = hashlib.sha256()
        while True:
            data = staging_file.read(self.DEFAULT_CHUNK_SIZE_BYTES)
            if not data:
                break
            assembled_sha256.update(data)

        if assembled_sha256.hexdigest() != expected_sha256.lower():
            raise ValueError("Assembled SHA-256 does not match the expected value.")
