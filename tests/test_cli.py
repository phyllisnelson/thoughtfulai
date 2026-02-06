import logging
from unittest.mock import MagicMock, patch

import pytest

from my_solution import main, parse_args
from routing_cycle_detector.streaming import is_url
from routing_cycle_detector.core import RoutingCycleDetector


class TestIsUrl:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("http://example.com/data.txt", True),
            ("https://example.com/data.txt", True),
            ("data.txt", False),
            ("/path/to/file.txt", False),
            ("ftp://example.com/file.txt", False),
        ],
        ids=["http", "https", "filename", "absolute_path", "ftp"],
    )
    def test_url_detection(self, value, expected):
        assert is_url(value) == expected


class TestParseArgs:
    def test_parses_input_source(self):
        args = parse_args(["test.txt"])
        assert args.input_source == "test.txt"

    def test_parses_url(self):
        args = parse_args(["https://example.com/data.txt"])
        assert args.input_source == "https://example.com/data.txt"

    def test_missing_input_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestMain:
    def test_success_with_cycle(self, routing_file, capsys):
        filepath = routing_file(
            [
                ("A", "B", "1", "100"),
                ("B", "A", "1", "100"),
            ]
        )
        exit_code = main([filepath])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "1,100,2" in captured.out

    def test_no_cycles_found(self, routing_file, caplog):
        filepath = routing_file(
            [
                ("A", "B", "1", "100"),
                ("B", "C", "1", "100"),
            ]
        )
        with caplog.at_level(logging.WARNING):
            exit_code = main([filepath])

        assert exit_code == 1
        assert "No cycles found" in caplog.text

    def test_file_not_found(self, caplog):
        with caplog.at_level(logging.ERROR):
            exit_code = main(["nonexistent_file.txt"])

        assert exit_code == 2
        assert "File not found" in caplog.text

    def test_not_a_file(self, tmp_path, caplog):
        with caplog.at_level(logging.ERROR):
            exit_code = main([str(tmp_path)])

        assert exit_code == 2
        assert "Not a file" in caplog.text

    def test_empty_file_no_cycles(self, empty_file, caplog):
        with caplog.at_level(logging.WARNING):
            exit_code = main([empty_file])

        assert exit_code == 1
        assert "No cycles found" in caplog.text

    def test_permission_denied(self, tmp_path, caplog, monkeypatch):
        filepath = tmp_path / "test.txt"
        filepath.write_text("A|B|1|100\n")

        def mock_run(self):
            raise PermissionError()

        monkeypatch.setattr(RoutingCycleDetector, "run", mock_run)
        with caplog.at_level(logging.ERROR):
            exit_code = main([str(filepath)])

        assert exit_code == 2
        assert "Permission denied" in caplog.text

    def test_unicode_decode_error(self, tmp_path, caplog, monkeypatch):
        filepath = tmp_path / "test.txt"
        filepath.write_text("valid content")

        def mock_run(self):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        monkeypatch.setattr(RoutingCycleDetector, "run", mock_run)
        with caplog.at_level(logging.ERROR):
            exit_code = main([str(filepath)])

        assert exit_code == 2
        assert "not valid UTF-8" in caplog.text

    def test_url_success(self, capsys):
        content = b"A|B|1|100\nB|A|1|100\n"

        mock_response = MagicMock()
        mock_response.read.side_effect = [content, b""]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch(
            "routing_cycle_detector.streaming.urllib.request.urlopen",
            return_value=mock_response,
        ):
            exit_code = main(["https://example.com/data.txt"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "1,100,2" in captured.out

    def test_url_fetch_error(self, caplog):
        with patch(
            "routing_cycle_detector.streaming.urllib.request.urlopen"
        ) as mock_urlopen:
            mock_urlopen.side_effect = OSError("Connection refused")
            with caplog.at_level(logging.ERROR):
                exit_code = main(["https://example.com/data.txt"])

        assert exit_code == 2
        assert "Failed to process" in caplog.text
