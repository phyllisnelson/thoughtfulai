from collections import Counter

import pytest

from routing_cycle_detector.core import (
    AnalysisResult,
    CycleResult,
    RoutingCycleDetector,
)


class TestCycleResult:
    @pytest.mark.parametrize(
        "claim_id,status_code,length,expected",
        [
            ("123", "197", 3, "123,197,3"),
            ("abc", "def", 5, "abc,def,5"),
            ("1", "1", 1, "1,1,1"),
        ],
        ids=["numeric", "alpha", "single_char"],
    )
    def test_str_format(self, claim_id, status_code, length, expected):
        result = CycleResult(claim_id, status_code, length)
        assert str(result) == expected


class TestAnalysisResult:
    def test_avg_hops_per_claim(self):
        result = AnalysisResult(cycle=None, total_hops=10, num_claims=5)
        assert result.avg_hops_per_claim == 2.0

    def test_avg_hops_per_claim_zero_claims(self):
        result = AnalysisResult(cycle=None, total_hops=0, num_claims=0)
        assert result.avg_hops_per_claim == 0


class TestRoutingCycleDetector:
    @pytest.mark.parametrize(
        "routes,expected_claim,expected_status,expected_length",
        [
            pytest.param(
                [
                    ("Epic", "Availity", "123", "197"),
                    ("Availity", "Optum", "123", "197"),
                    ("Optum", "Epic", "123", "197"),
                    ("Epic", "Availity", "891", "45"),
                    ("Availity", "Epic", "891", "45"),
                ],
                "123",
                "197",
                3,
                id="example_3_node_wins",
            ),
            pytest.param(
                [("A", "B", "1", "100"), ("B", "A", "1", "100")],
                "1",
                "100",
                2,
                id="simple_2_node",
            ),
            pytest.param(
                [("A", "A", "1", "100")],
                "1",
                "100",
                1,
                id="self_loop",
            ),
            pytest.param(
                [
                    ("A", "B", "1", "100"),
                    ("B", "A", "1", "100"),
                    ("X", "Y", "2", "200"),
                    ("Y", "Z", "2", "200"),
                    ("Z", "W", "2", "200"),
                    ("W", "X", "2", "200"),
                ],
                "2",
                "200",
                4,
                id="longest_of_multiple",
            ),
            pytest.param(
                [
                    ("A", "B", "1", "100"),
                    ("B", "C", "1", "100"),
                    ("C", "A", "1", "100"),
                    ("A", "B", "1", "200"),
                    ("B", "A", "1", "200"),
                ],
                "1",
                "100",
                3,
                id="separate_status_codes",
            ),
            pytest.param(
                [
                    ("X", "Y", "2", "200"),
                    ("Y", "Z", "2", "200"),
                    ("Z", "X", "2", "200"),
                    ("A", "B", "1", "100"),
                    ("B", "C", "1", "100"),
                    ("C", "A", "1", "100"),
                ],
                "1",
                "100",
                3,
                id="tiebreaker_same_length_smaller_claim_id",
            ),
            pytest.param(
                [
                    ("A", "B", "1", "200"),
                    ("B", "C", "1", "200"),
                    ("C", "A", "1", "200"),
                    ("X", "Y", "1", "100"),
                    ("Y", "Z", "1", "100"),
                    ("Z", "X", "1", "100"),
                ],
                "1",
                "100",
                3,
                id="tiebreaker_same_length_smaller_status_code",
            ),
        ],
    )
    def test_cycle_detection(
        self, routing_file, routes, expected_claim, expected_status, expected_length
    ):
        filepath = routing_file(routes)
        result = RoutingCycleDetector(filepath).run()

        assert result.cycle is not None
        assert result.cycle.claim_id == expected_claim
        assert result.cycle.status_code == expected_status
        assert result.cycle.cycle_length == expected_length
        assert result.total_hops == len(routes)

    @pytest.mark.parametrize(
        "routes",
        [
            [("A", "B", "1", "100"), ("B", "C", "1", "100"), ("C", "D", "1", "100")],
            [],
        ],
        ids=["linear_chain", "empty_routes"],
    )
    def test_no_cycle(self, routing_file, routes):
        filepath = routing_file(routes)
        result = RoutingCycleDetector(filepath).run()
        assert result.cycle is None
        assert result.total_hops == len(routes)

    def test_cycles_per_status(self, routing_file):
        routes = [
            ("A", "B", "1", "100"),
            ("B", "A", "1", "100"),
            ("X", "Y", "2", "200"),
            ("Y", "Z", "2", "200"),
            ("Z", "X", "2", "200"),
            ("P", "Q", "3", "100"),
            ("Q", "P", "3", "100"),
        ]
        filepath = routing_file(routes)
        result = RoutingCycleDetector(filepath).run()

        assert result.cycles_per_status == Counter({"100": 2, "200": 1})

    def test_shorter_cycle_does_not_replace_longer(self, routing_file):
        routes = [
            ("A", "B", "1", "100"),
            ("B", "C", "1", "100"),
            ("C", "A", "1", "100"),
            ("X", "Y", "1", "100"),
            ("Y", "X", "1", "100"),
        ]
        filepath = routing_file(routes)
        result = RoutingCycleDetector(filepath).run()

        assert result.cycle is not None
        assert result.cycle.cycle_length == 3

    def test_no_cycles_empty_cycles_per_status(self, routing_file):
        routes = [("A", "B", "1", "100"), ("B", "C", "1", "100")]
        filepath = routing_file(routes)
        result = RoutingCycleDetector(filepath).run()

        assert result.cycles_per_status == Counter()

    def test_empty_file(self, empty_file):
        result = RoutingCycleDetector(empty_file).run()
        assert result.cycle is None
        assert result.total_hops == 0
        assert result.num_claims == 0
        assert result.cycles_per_status == Counter()

    @pytest.mark.parametrize(
        "content,expected_length",
        [
            ("\nA|B|1|100\n\nB|A|1|100\n\n", 2),
            ("A|B|1|100\ninvalid line\nB|A|1|100\nA|B|C\n", 2),
        ],
        ids=["blank_lines", "malformed_lines"],
    )
    def test_ignores_invalid_lines(self, tmp_path, content, expected_length):
        filepath = tmp_path / "test.txt"
        filepath.write_text(content)
        result = RoutingCycleDetector(str(filepath)).run()

        assert result.cycle is not None
        assert result.cycle.cycle_length == expected_length
