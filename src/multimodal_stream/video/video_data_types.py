from dataclasses import dataclass


@dataclass(frozen=True)
class VideoChunk:
    chunk_index: int
    chunk_count: int
    offset_bytes: int
    data: bytes
    sha256: str

    @property
    def size_bytes(self) -> int:
        return len(self.data)
