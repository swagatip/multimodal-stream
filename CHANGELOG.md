# Changelog

Notable changes to this project are recorded here.

## [Unreleased]

### Added

- Video file chunking with configurable chunk sizes, byte offsets, and per-chunk SHA-256 checksums.
- Local video chunk assembly with manifest validation and per-chunk and whole-file SHA-256 checksums.
- Typed message contracts for video chunk metadata and video completion manifests.
- S3-compatible object storage adapter with a local SeaweedFS setup and chunk upload/download integration test.

## [v0.1.0] - 2026-11-13
### Added

- Local single-node Kafka broker configuration using Docker Compose and KRaft.
- Python topic initialization script for the `messages` topic.
- Python producer and consumer classes for sending and receiving UTF-8 text messages.
- Unit tests for producer delivery failures and integration tests for message round trips.
