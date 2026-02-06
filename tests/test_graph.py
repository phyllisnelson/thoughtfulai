import pytest

from routing_cycle_detector.graph import (
    _dfs_find_cycle,
    build_graph,
    find_longest_cycle,
    tarjan_sccs,
)
from routing_cycle_detector.streaming import Edge


class TestBuildGraph:
    def test_builds_adjacency_list(self):
        edges = [Edge("A", "B"), Edge("B", "C"), Edge("A", "C")]
        graph, nodes = build_graph(edges)

        assert graph["A"] == ["B", "C"]
        assert graph["B"] == ["C"]
        assert nodes == {"A", "B", "C"}

    def test_deduplicates_edges(self):
        edges = [Edge("A", "B"), Edge("A", "B"), Edge("B", "C"), Edge("A", "B")]
        graph, nodes = build_graph(edges)

        assert graph["A"] == ["B"]
        assert graph["B"] == ["C"]
        assert nodes == {"A", "B", "C"}

    def test_empty_edges(self):
        graph, nodes = build_graph([])

        assert len(graph) == 0
        assert len(nodes) == 0


class TestTarjanSccs:
    def test_single_scc(self):
        graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
        sccs = tarjan_sccs(graph, {"A", "B", "C"})

        assert len(sccs) == 1
        assert set(sccs[0]) == {"A", "B", "C"}

    def test_multiple_sccs(self):
        graph = {"A": ["B"], "B": ["A"], "X": ["Y"], "Y": ["X"]}
        sccs = tarjan_sccs(graph, {"A", "B", "X", "Y"})
        scc_sets = [set(scc) for scc in sccs]

        assert len(sccs) == 2
        assert {"A", "B"} in scc_sets
        assert {"X", "Y"} in scc_sets

    def test_acyclic_gives_singletons(self):
        graph = {"A": ["B"], "B": ["C"], "C": []}
        sccs = tarjan_sccs(graph, {"A", "B", "C"})

        assert len(sccs) == 3
        assert all(len(scc) == 1 for scc in sccs)

    def test_self_loop_scc(self):
        graph = {"A": ["A"]}
        sccs = tarjan_sccs(graph, {"A"})

        assert len(sccs) == 1
        assert sccs[0] == ["A"]

    def test_mixed_cyclic_and_acyclic(self):
        graph = {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": []}
        sccs = tarjan_sccs(graph, {"A", "B", "C", "D"})
        scc_sets = [set(scc) for scc in sccs]

        assert {"A", "B", "C"} in scc_sets
        assert {"D"} in scc_sets


class TestDfsFindCycle:
    @pytest.mark.parametrize(
        "graph,start,expected",
        [
            ({"A": ["B"], "B": ["C"], "C": ["A"]}, "A", 3),
            ({"A": ["B"], "B": ["C"], "C": []}, "A", 0),
            ({"A": ["A"]}, "A", 1),
            ({"A": ["B", "C"], "B": ["C"], "C": ["A"]}, "A", 3),
        ],
        ids=["simple_cycle", "no_cycle", "self_loop", "multiple_paths"],
    )
    def test_dfs_cycle_detection(self, graph, start, expected):
        assert _dfs_find_cycle(graph, start) == expected

    def test_skips_visited_non_start_neighbor(self):
        """DFS encounters already-visited node that isn't start."""
        graph = {"A": ["B"], "B": ["C"], "C": ["B", "A"]}
        assert _dfs_find_cycle(graph, "A") == 3


class TestFindLongestCycle:
    def test_empty_edges_returns_zero(self):
        assert find_longest_cycle([]) == 0

    def test_cycle_with_acyclic_tail(self):
        edges = [Edge("A", "B"), Edge("B", "A"), Edge("C", "A")]
        assert find_longest_cycle(edges) == 2

    def test_duplicate_edges_handled(self):
        edges = [Edge("A", "B"), Edge("B", "A"), Edge("A", "B"), Edge("B", "A")]
        assert find_longest_cycle(edges) == 2

    def test_cycle_with_outgoing_cross_scc_edge(self):
        """Cycle node has out-edge to non-cycle node."""
        edges = [Edge("A", "B"), Edge("B", "A"), Edge("A", "C")]
        assert find_longest_cycle(edges) == 2
