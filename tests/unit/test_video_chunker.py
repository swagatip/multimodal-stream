import hashlib
import logging
import tempfile
import unittest
from logging.config import fileConfig
from pathlib import Path

from multimodal_stream.video_chunker import VideoChunker

fileConfig(
    Path(__file__).with_name("logging.ini"),
    disable_existing_loggers=False,
)

class VideoChunkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunker = VideoChunker()

    def test_create_chunks_splits_data_and_preserves_offsets(self) -> None:
        data = bytes(range(130))
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            video_path.write_bytes(data)

            chunks = list(self.chunker.create_chunks(video_path, chunk_size=64))

        self.assertEqual(len(chunks), 3)
        self.assertEqual([chunk.chunk_index for chunk in chunks], [0, 1, 2])
        self.assertEqual([chunk.chunk_count for chunk in chunks], [3, 3, 3])
        self.assertEqual([chunk.offset_bytes for chunk in chunks], [0, 64, 128])
        self.assertEqual([len(chunk.data) for chunk in chunks], [64, 64, 2])
        self.assertEqual(
            [chunk.sha256 for chunk in chunks],
            [
                hashlib.sha256(data[:64]).hexdigest(),
                hashlib.sha256(data[64:128]).hexdigest(),
                hashlib.sha256(data[128:]).hexdigest(),
            ],
        )
        self.assertEqual(b"".join(chunk.data for chunk in chunks), data)

    def test_create_chunks_uses_default_chunk_size(self) -> None:
        data = bytes(VideoChunker.DEFAULT_CHUNK_SIZE_BYTES + 1)
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            video_path.write_bytes(data)

            chunks = list(self.chunker.create_chunks(video_path))

        self.assertEqual(
            [len(chunk.data) for chunk in chunks],
            [VideoChunker.DEFAULT_CHUNK_SIZE_BYTES, 1],
        )

    def test_create_chunks_does_not_add_empty_chunk_for_exact_multiple(self) -> None:
        data = bytes(range(128))
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            video_path.write_bytes(data)

            chunks = list(self.chunker.create_chunks(video_path, chunk_size=64))

        self.assertEqual(len(chunks), 2)
        self.assertEqual([chunk.offset_bytes for chunk in chunks], [0, 64])
        self.assertEqual(b"".join(chunk.data for chunk in chunks), data)

    def test_create_chunks_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "missing.mp4"

            with self.assertRaises(FileNotFoundError):
                list(self.chunker.create_chunks(video_path, chunk_size=64))

    def test_create_chunks_warns_and_yields_no_chunks_for_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "empty.mp4"
            video_path.touch()

            with self.assertLogs(
                "multimodal_stream.video_chunker", level=logging.WARNING
            ):
                chunks = list(self.chunker.create_chunks(video_path, chunk_size=64))

        self.assertEqual(chunks, [])

    def test_create_chunks_rejects_non_positive_chunk_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "video.mp4"
            video_path.write_bytes(b"data")

            for chunk_size in (0, -1):
                with self.subTest(chunk_size=chunk_size):
                    with self.assertRaises(ValueError):
                        list(
                            self.chunker.create_chunks(
                                video_path, chunk_size=chunk_size
                            )
                        )