import hashlib
import tempfile
import unittest
from dataclasses import replace
from logging.config import fileConfig
from pathlib import Path

from multimodal_stream.video.video_assembler import VideoAssembler
from multimodal_stream.video.video_data_types import VideoChunk
from multimodal_stream.video.video_chunker import VideoChunker

fileConfig(
    Path(__file__).parent.parent / "logging.ini",
    disable_existing_loggers=False,
)

class VideoAssemblerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assembler = VideoAssembler()

    def test_stitch_chunks_reassembles_out_of_order_chunks(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            result_path = self.assembler.stitch_chunks(
                reversed(chunks),
                output_path,
                expected_size_bytes=len(data),
                expected_sha256=hashlib.sha256(data).hexdigest(),
                expected_chunk_count=3,
            )

            self.assertEqual(result_path, output_path)
            self.assertEqual(output_path.read_bytes(), data)

    def test_stitch_chunks_creates_empty_file_for_empty_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            self.assembler.stitch_chunks(
                [],
                output_path,
                expected_size_bytes=0,
                expected_sha256=hashlib.sha256(b"").hexdigest(),
                expected_chunk_count=0,
            )

            self.assertEqual(output_path.read_bytes(), b"")

    def test_stitch_chunks_rejects_missing_chunk_without_replacing_output(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            output_path.write_bytes(b"existing output")

            with self.assertRaisesRegex(ValueError, "Missing video chunks"):
                self.assembler.stitch_chunks(
                    chunks[:-1],
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

            self.assertEqual(output_path.read_bytes(), b"existing output")

    def test_stitch_chunks_rejects_chunk_count_mismatching_manifest(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)
        inconsistent_chunk = replace(chunks[0], chunk_count=4)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            with self.assertRaisesRegex(ValueError, "expected 3"):
                self.assembler.stitch_chunks(
                    [inconsistent_chunk, *chunks[1:]],
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

    def test_stitch_chunks_rejects_duplicate_chunk(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            with self.assertRaisesRegex(ValueError, "Duplicate video chunk"):
                self.assembler.stitch_chunks(
                    [*chunks, chunks[0]],
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

    def test_stitch_chunks_rejects_corrupted_chunk(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)
        corrupted_chunk = replace(chunks[1], data=b"corrupted")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                self.assembler.stitch_chunks(
                    [chunks[0], corrupted_chunk, chunks[2]],
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

    def test_stitch_chunks_rejects_incorrect_offset(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)
        incorrectly_offset_chunk = replace(chunks[1], offset_bytes=65)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            
            with self.assertRaisesRegex(ValueError, "Unexpected offset"):
                self.assembler.stitch_chunks(
                    [chunks[0], incorrectly_offset_chunk, chunks[2]],
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

    def test_stitch_chunks_rejects_manifest_size_mismatch(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            
            with self.assertRaisesRegex(ValueError, "Assembled size mismatch"):
                self.assembler.stitch_chunks(
                    chunks,
                    output_path,
                    expected_size_bytes=len(data) + 1,
                    expected_sha256=hashlib.sha256(data).hexdigest(),
                    expected_chunk_count=3,
                )

    def test_stitch_chunks_rejects_manifest_checksum_mismatch(self) -> None:
        data = bytes(range(130))
        chunks = self._create_chunks(data, chunk_size=64)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            output_path.write_bytes(b"existing output")

            with self.assertRaisesRegex(ValueError, "Assembled SHA-256"):
                self.assembler.stitch_chunks(
                    chunks,
                    output_path,
                    expected_size_bytes=len(data),
                    expected_sha256=hashlib.sha256(b"different data").hexdigest(),
                    expected_chunk_count=3,
                )

            self.assertEqual(output_path.read_bytes(), b"existing output")

    def test_stitch_chunks_rejects_malformed_manifest_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            
            for expected_sha256 in ("", "a" * 63, "g" * 64):
                with self.subTest(expected_sha256=expected_sha256):
                    with self.assertRaisesRegex(ValueError, "expected_sha256"):
                        self.assembler.stitch_chunks(
                            [],
                            output_path,
                            expected_size_bytes=0,
                            expected_sha256=expected_sha256,
                            expected_chunk_count=0,
                        )

    def test_stitch_chunks_rejects_negative_manifest_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "assembled.mp4"
            
            with self.assertRaisesRegex(ValueError, "expected_size_bytes"):
                self.assembler.stitch_chunks(
                    [],
                    output_path,
                    expected_size_bytes=-1,
                    expected_sha256=hashlib.sha256(b"").hexdigest(),
                    expected_chunk_count=0,
                )

    @staticmethod
    def _create_chunks(data: bytes, chunk_size: int) -> list[VideoChunk]:
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = Path(temp_dir) / "source.mp4"
            video_path.write_bytes(data)
            return list(VideoChunker().create_chunks(video_path, chunk_size))
