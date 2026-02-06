# Routing Cycle Detector

[![CI](https://github.com/USERNAME/routing-cycle-detector/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/routing-cycle-detector/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Finds the longest routing cycle in a claim routing file where all hops share the same `claim_id` and `status_code`.

## Installation

```bash
# Clone the repository
git clone https://github.com/USERNAME/routing-cycle-detector.git
cd routing-cycle-detector

# Install (production)
pip install -e .

# Install (development)
make install-dev
```

## Usage

```bash
python3 my_solution.py <input_file_or_url>

# Or after installation:
routing-cycle-detector <input_file_or_url>
```

Examples:
```bash
# Local file
python3 my_solution.py large_input_v1.txt
# Output: 190017,190116,10

# URL
python3 my_solution.py https://example.com/routing_data.txt
# Output: 3,102,4
```

### CLI Options

```bash
python3 my_solution.py --help
python3 my_solution.py --version
```

## Development

```bash
# Install dev dependencies
make install-dev

# Run tests
make test

# Run linters
make lint

# Format code
make format

# Type checking
make typecheck

# See all commands
make help
```

## Strategy

Hash-bucketing with SCC-pruned cycle detection:

1. **Bucket** — stream input, hash each `(claim_id, status_code)` to one of 128 temp files
2. **Group** — read each bucket, collect edges by `(claim_id, status_code)`
3. **Build** — deduplicated directed graph per group
4. **SCC** — Tarjan's algorithm (iterative) to find strongly connected components
5. **DFS** — exhaustive backtracking within each SCC to find the longest simple cycle
6. **Discard** — free edges before processing the next group

## Complexity

- **Time:** O(N) bucketing + O(N) read + O(V + E) SCC + O(V × paths) cycle enumeration per group
- **Memory:** O(edges per bucket) — one bucket in memory at a time

## Pros/Cons

| Pros | Cons |
|------|------|
| Pure Python stdlib — no external dependencies | 128 temp files during bucketing |
| Memory-efficient — one bucket at a time | Bucket sizes depend on hash distribution |
| Tarjan's SCC prunes acyclic nodes before DFS | |
| Edge deduplication avoids redundant traversal | |

## Project Structure

```
├── routing_cycle_detector/
│   ├── __init__.py      # Package exports
│   ├── core.py          # CycleResult dataclass and RoutingCycleDetector orchestrator
│   ├── graph.py         # Pure graph algorithms (Tarjan's SCC, DFS, build_graph)
│   └── streaming.py     # Hash-bucketing and group streaming
├── my_solution.py       # CLI entry point (argparse, main)
├── pyproject.toml       # Package configuration and tool settings
├── Makefile             # Development commands (test, lint, coverage)
├── tests/
│   ├── conftest.py      # pytest fixtures (routing_file, empty_file)
│   ├── test_core.py     # Tests for orchestration and CycleResult
│   ├── test_graph.py    # Tests for graph algorithms (SCC, DFS, dedup)
│   ├── test_streaming.py # Tests for bucketing and streaming
│   └── test_cli.py      # Tests for CLI
└── .pre-commit-config.yaml
```
