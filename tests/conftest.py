"""Pytest fixtures for routing cycle detector tests."""

from pathlib import Path

import pytest


@pytest.fixture
def routing_file(tmp_path: Path):
    """Factory fixture to create routing data files.

    Usage:
        def test_example(routing_file):
            filepath = routing_file([
                ("Epic", "Availity", "123", "197"),
                ("Availity", "Optum", "123", "197"),
            ])
    """

    def _create_file(routes: list[tuple[str, str, str, str]]) -> str:
        content = "\n".join(
            f"{src}|{dst}|{claim}|{status}" for src, dst, claim, status in routes
        )
        filepath = tmp_path / "routes.txt"
        filepath.write_text(content + "\n" if content else "")
        return str(filepath)

    return _create_file


@pytest.fixture
def empty_file(tmp_path: Path) -> str:
    """Create an empty routing file."""
    filepath = tmp_path / "empty.txt"
    filepath.write_text("")
    return str(filepath)
