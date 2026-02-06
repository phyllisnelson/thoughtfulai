"""Orchestration: wires GroupStreamer + graph algorithms together."""

from dataclasses import dataclass
from typing import Optional

from .graph import find_longest_cycle
from .streaming import GroupStreamer


@dataclass
class CycleResult:
    """Result of cycle detection.

    Attributes:
        claim_id: The claim identifier for the cycle.
        status_code: The status code for the cycle.
        cycle_length: Number of hops in the cycle.
    """

    claim_id: str
    status_code: str
    cycle_length: int

    def __str__(self) -> str:
        return f"{self.claim_id},{self.status_code},{self.cycle_length}"


class RoutingCycleDetector:
    """Detects routing cycles in claim routing data."""

    def __init__(self, filepath: str) -> None:
        """Initialize detector with input file path.

        Args:
            filepath: Path to routing data file or URL.
        """
        self.filepath = filepath

    def run(self) -> Optional[CycleResult]:
        """Detect the longest routing cycle in the input file.

        Returns:
            CycleResult for the longest cycle found, or None if no cycles exist.
        """
        best_result: Optional[CycleResult] = None
        streamer = GroupStreamer(self.filepath)

        for group_key, edges in streamer.stream_groups():
            cycle_length = find_longest_cycle(edges)
            if cycle_length > 0:
                candidate = CycleResult(
                    group_key.claim_id, group_key.status_code, cycle_length
                )
                if self._is_better_result(candidate, best_result):
                    best_result = candidate

        return best_result

    def _is_better_result(
        self, candidate: CycleResult, current_best: Optional[CycleResult]
    ) -> bool:
        """Check if candidate should replace current best.

        Prefers longer cycles. Ties broken by lexicographically smallest
        (claim_id, status_code).

        Args:
            candidate: New cycle result to evaluate.
            current_best: Current best result (may be None).

        Returns:
            True if candidate should replace current_best.
        """
        if current_best is None:
            return True
        if candidate.cycle_length > current_best.cycle_length:
            return True
        if candidate.cycle_length == current_best.cycle_length:
            return (candidate.claim_id, candidate.status_code) < (
                current_best.claim_id,
                current_best.status_code,
            )
        return False
