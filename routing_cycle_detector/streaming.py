"""File streaming and hash-bucketing utilities."""

import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Iterator, NamedTuple

# Constants
FIELD_DELIMITER = "|"
CHUNK_SIZE = 8192  # Bytes to read at a time from URL
EXPECTED_FIELD_COUNT = 4
NUM_BUCKETS = 128  # Number of hash buckets for partitioning

# Field indices in the input format: source|destination|claim_id|status_code
SOURCE_IDX = 0
DESTINATION_IDX = 1
CLAIM_ID_IDX = 2
STATUS_CODE_IDX = 3


def is_url(s: str) -> bool:
    """Check if string looks like a URL."""
    return s.startswith(("http://", "https://"))


class GroupKey(NamedTuple):
    """Key identifying a group of edges.

    Attributes:
        claim_id: The claim identifier.
        status_code: The status code.
    """

    claim_id: str
    status_code: str


class Edge(NamedTuple):
    """A directed edge between systems.

    Attributes:
        source: The source system name.
        destination: The destination system name.
    """

    source: str
    destination: str


# Type alias for a group of edges sharing the same key
EdgeGroup = tuple[GroupKey, list[Edge]]


class GroupStreamer:
    """Streams groups of edges using hash-bucketing.

    Partitions the input file into N temp bucket files by hashing
    (claim_id, status_code), then processes each bucket independently.
    Memory usage: O(edges per bucket).

    Attributes:
        filepath: Path to the input file or URL.
    """

    def __init__(self, filepath: str) -> None:
        """Initialize streamer with input file path.

        Args:
            filepath: Path to routing data file or URL.
        """
        self.filepath = filepath

    def stream_groups(self) -> Iterator[EdgeGroup]:
        """Bucket file by group key, then stream groups.

        Yields:
            Tuples of (GroupKey, list of Edges) for each group.
        """
        # For URLs, download to temp file first
        if self._is_url():
            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=".txt", delete=False
            ) as tmp:
                with urllib.request.urlopen(self.filepath) as response:
                    for chunk in iter(lambda: response.read(CHUNK_SIZE), b""):
                        tmp.write(chunk)
                local_path = tmp.name
        else:
            local_path = self.filepath

        # Partition file into hash buckets
        bucket_paths = self._bucket_file(local_path)

        try:
            yield from self._stream_groups_from_buckets(bucket_paths)
        finally:
            # Cleanup any remaining bucket files
            for bp in bucket_paths:
                Path(bp).unlink(missing_ok=True)
            if self._is_url():
                Path(local_path).unlink(missing_ok=True)

    def _is_url(self) -> bool:
        """Check if filepath is a URL.

        Returns:
            True if filepath starts with http:// or https://.
        """
        return is_url(self.filepath)

    def _bucket_file(self, filepath: str) -> list[str]:
        """Partition input into N temp files by hash(claim_id, status_code).

        Args:
            filepath: Path to the file to partition.

        Returns:
            List of paths to the bucket temp files.
        """
        bucket_handles = []
        bucket_paths: list[str] = []

        try:
            for i in range(NUM_BUCKETS):
                f = tempfile.NamedTemporaryFile(
                    mode="w", suffix=f".bucket{i}.txt", delete=False
                )
                bucket_paths.append(f.name)
                bucket_handles.append(f)

            with open(filepath, "r", encoding="utf-8") as infile:
                for line in infile:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    parts = stripped.split(FIELD_DELIMITER)
                    if len(parts) != EXPECTED_FIELD_COUNT:
                        continue
                    key = (parts[CLAIM_ID_IDX], parts[STATUS_CODE_IDX])
                    bucket_idx = hash(key) % NUM_BUCKETS
                    bucket_handles[bucket_idx].write(stripped + "\n")
        finally:
            for f in bucket_handles:
                f.close()

        return bucket_paths

    def _stream_groups_from_buckets(
        self, bucket_paths: list[str]
    ) -> Iterator[EdgeGroup]:
        """Process each bucket: group by key, yield groups.

        Args:
            bucket_paths: List of paths to bucket files.

        Yields:
            Tuples of (GroupKey, list of Edges) for each group.
        """
        for bucket_path in bucket_paths:
            groups: dict[GroupKey, list[Edge]] = defaultdict(list)

            with open(bucket_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    parts = stripped.split(FIELD_DELIMITER)
                    if len(parts) != EXPECTED_FIELD_COUNT:
                        continue
                    key = GroupKey(parts[CLAIM_ID_IDX], parts[STATUS_CODE_IDX])
                    edge = Edge(parts[SOURCE_IDX], parts[DESTINATION_IDX])
                    groups[key].append(edge)

            # Yield groups sorted by key within this bucket
            for key in sorted(groups):
                yield key, groups[key]

            # Clean up this bucket immediately
            Path(bucket_path).unlink(missing_ok=True)
