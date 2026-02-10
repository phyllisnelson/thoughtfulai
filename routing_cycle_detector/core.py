"""Orchestration: wires GroupStreamer + graph algorithms together."""

from collections import Counter
from dataclasses import dataclass, field
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


@dataclass
class AnalysisResult:
    """Full analysis result including cycle detection and cost metrics.

    Attributes:
        cycle: The longest cycle found, or None if no cycles exist.
        total_hops: Total number of hops (edges) across all groups.
        num_claims: Number of distinct claim IDs seen.
        cycles_per_status: Count of cycles detected per status code.
        avg_hops_per_claim: Average number of hops per claim.
    """

    cycle: Optional[CycleResult]
    total_hops: int
    num_claims: int
    cycles_per_status: Counter[str] = field(default_factory=Counter)

    @property
    def avg_hops_per_claim(self) -> float:
        if self.num_claims == 0:
            return 0

        return self.total_hops / self.num_claims

    @property
    def top_claim_status_codes(self) -> list[tuple[str, int]]:
        return self.cycles_per_status.most_common(5)

    def print_summary(self) -> None:
        """Print a formatted summary of the analysis results."""
        print(f"Total hops: {self.total_hops}")
        print(f"Num claims: {self.num_claims}")
        print(f"Avg hops/claim: {self.avg_hops_per_claim:.2f}")

        if self.top_claim_status_codes:
            print("Top status codes in cycles:")
            for status, count in self.top_claim_status_codes:
                print(f"  {status}: {count}")

        if self.cycle:
            print(f"Longest cycle: {self.cycle}")
        else:
            print("No cycles found")


class RoutingCycleDetector:
    """Detects routing cycles in claim routing data."""

    def __init__(self, filepath: str) -> None:
        """Initialize detector with input file path.

        Args:
            filepath: Path to routing data file or URL.
        """
        self.filepath = filepath

    def run(self) -> AnalysisResult:
        """Detect the longest routing cycle and count total hops.

        Returns:
            AnalysisResult with the longest cycle and total hop count.
        """
        best_result: Optional[CycleResult] = None
        total_hops = 0
        claims: set[str] = set()
        cycles_per_status: Counter[str] = Counter()
        streamer = GroupStreamer(self.filepath)

        for group_key, edges in streamer.stream_groups():
            total_hops += len(edges)
            claims.add(group_key.claim_id)

            cycle_length = find_longest_cycle(edges)
            if cycle_length > 0:
                cycles_per_status[group_key.status_code] += 1
                candidate = CycleResult(
                    group_key.claim_id, group_key.status_code, cycle_length
                )
                if self._is_better_result(candidate, best_result):
                    best_result = candidate

        return AnalysisResult(
            cycle=best_result,
            total_hops=total_hops,
            num_claims=len(claims),
            cycles_per_status=cycles_per_status,
        )

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
