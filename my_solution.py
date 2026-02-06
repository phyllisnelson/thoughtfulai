"""
Routing Cycle Detector CLI

Command-line interface for detecting routing cycles in claim routing files.
"""

import argparse
import logging
import sys
from pathlib import Path

from routing_cycle_detector.core import RoutingCycleDetector
from routing_cycle_detector.streaming import is_url

logger = logging.getLogger(__name__)


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="routing-cycle-detector",
        description="Find the longest routing cycle in a claim routing file.",
        epilog="Example: python3 my_solution.py large_input_v1.txt",
    )
    parser.add_argument(
        "input_source",
        help="Path to input file or URL containing routing data",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )
    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point. Returns 0=success, 1=no cycles, 2=error."""
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s: %(message)s"
    )

    input_source: str = parse_args(args).input_source

    # Validate local file exists
    if not is_url(input_source):
        path = Path(input_source)
        if not path.exists():
            logger.error("File not found: %s", input_source)
            return 2
        if not path.is_file():
            logger.error("Not a file: %s", input_source)
            return 2

    try:
        result = RoutingCycleDetector(input_source).run()
    except PermissionError:
        logger.error("Permission denied: %s", input_source)
        return 2
    except UnicodeDecodeError:
        logger.error("Content is not valid UTF-8: %s", input_source)
        return 2
    except Exception as e:
        logger.error("Failed to process: %s", e)
        return 2

    if result:
        print(result)
        return 0

    logger.warning("No cycles found")
    return 1


if __name__ == "__main__":
    sys.exit(main())
