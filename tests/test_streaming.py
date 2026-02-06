import pytest

from routing_cycle_detector.streaming import Edge, GroupKey, GroupStreamer


class TestGroupKey:
    def test_namedtuple_fields(self):
        key = GroupKey(claim_id="123", status_code="456")
        assert key.claim_id == "123"
        assert key.status_code == "456"

    def test_equality(self):
        key1 = GroupKey("a", "b")
        key2 = GroupKey("a", "b")
        key3 = GroupKey("a", "c")
        assert key1 == key2
        assert key1 != key3

    def test_ordering(self):
        keys = [GroupKey("2", "a"), GroupKey("1", "b"), GroupKey("1", "a")]
        assert sorted(keys) == [
            GroupKey("1", "a"),
            GroupKey("1", "b"),
            GroupKey("2", "a"),
        ]


class TestEdge:
    def test_namedtuple_fields(self):
        edge = Edge(source="A", destination="B")
        assert edge.source == "A"
        assert edge.destination == "B"

    def test_equality(self):
        edge1 = Edge("A", "B")
        edge2 = Edge("A", "B")
        edge3 = Edge("A", "C")
        assert edge1 == edge2
        assert edge1 != edge3


class TestGroupStreamerIsUrl:
    @pytest.mark.parametrize(
        "filepath,expected",
        [
            ("http://example.com/file.txt", True),
            ("https://example.com/file.txt", True),
            ("file.txt", False),
            ("/path/to/file.txt", False),
            ("ftp://example.com/file.txt", False),
        ],
        ids=["http", "https", "relative", "absolute", "ftp"],
    )
    def test_is_url(self, filepath, expected):
        streamer = GroupStreamer(filepath)
        assert streamer._is_url() == expected


class TestGroupStreamer:
    def test_single_group(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("A|B|1|100\nB|C|1|100\nC|A|1|100\n")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 1
        key, edges = groups[0]
        assert key == GroupKey("1", "100")
        assert len(edges) == 3

    def test_multiple_groups(self, tmp_path):
        filepath = tmp_path / "test.txt"
        # Unsorted input - groups should still be yielded correctly after bucketing
        filepath.write_text("A|B|2|200\nX|Y|1|100\nB|A|2|200\nY|X|1|100\n")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 2
        keys = {g[0] for g in groups}
        assert GroupKey("1", "100") in keys
        assert GroupKey("2", "200") in keys

    def test_empty_file(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 0

    def test_skips_blank_lines(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("\nA|B|1|100\n\nB|A|1|100\n\n")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 1
        _, edges = groups[0]
        assert len(edges) == 2

    def test_skips_malformed_lines(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("A|B|1|100\ninvalid\nB|A|1|100\ntoo|few|fields\n")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 1
        _, edges = groups[0]
        assert len(edges) == 2

    def test_preserves_edge_order_within_group(self, tmp_path):
        filepath = tmp_path / "test.txt"
        # All same group, edges should maintain relative order
        filepath.write_text("A|B|1|100\nB|C|1|100\nC|D|1|100\n")

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        _, edges = groups[0]
        assert edges[0] == Edge("A", "B")
        assert edges[1] == Edge("B", "C")
        assert edges[2] == Edge("C", "D")

    def test_many_groups(self, tmp_path):
        filepath = tmp_path / "test.txt"
        lines = [f"A|B|{i}|100\n" for i in range(100)]
        filepath.write_text("".join(lines))

        streamer = GroupStreamer(str(filepath))
        groups = list(streamer.stream_groups())

        assert len(groups) == 100

    def test_bucket_reader_handles_blank_and_malformed_lines(self, tmp_path):
        """Cover defensive guards in _stream_groups_from_buckets."""
        # Write a fake bucket file with blank and malformed lines injected
        bucket_file = tmp_path / "bucket.txt"
        bucket_file.write_text("\nA|B|1|100\n\nbad|line\nB|A|1|100\n")

        streamer = GroupStreamer(str(tmp_path / "dummy.txt"))
        groups = list(streamer._stream_groups_from_buckets([str(bucket_file)]))

        assert len(groups) == 1
        _, edges = groups[0]
        assert len(edges) == 2

    def test_temp_files_cleaned_up(self, tmp_path):
        import os

        filepath = tmp_path / "test.txt"
        filepath.write_text("A|B|1|100\n")

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        original_temp = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(temp_dir)

        try:
            streamer = GroupStreamer(str(filepath))
            list(streamer.stream_groups())

            # Temp files should be cleaned up
            temp_files = list(temp_dir.glob("*.txt"))
            assert len(temp_files) == 0
        finally:
            if original_temp:
                os.environ["TMPDIR"] = original_temp
            elif "TMPDIR" in os.environ:
                del os.environ["TMPDIR"]
