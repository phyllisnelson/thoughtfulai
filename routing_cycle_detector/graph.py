"""Pure graph algorithms for cycle detection."""

from collections import defaultdict
from typing import Iterator

from .streaming import Edge

# Type aliases
Graph = dict[str, list[str]]
NodeSet = set[str]

MAX_PATH_LENGTH = 1000


def find_longest_cycle(edges: list[Edge]) -> int:
    """Find the longest simple cycle in a directed graph.

    Uses Tarjan's SCC algorithm to prune acyclic portions, then
    DFS backtracking within each SCC to find the longest cycle.

    Args:
        edges: List of directed edges forming the graph.

    Returns:
        Length of the longest cycle, or 0 if no cycles exist.
    """
    graph, nodes = build_graph(edges)
    if not nodes:
        return 0

    sccs = tarjan_sccs(graph, nodes)
    max_cycle_length = 0

    for scc in sccs:
        if len(scc) == 1:
            node = scc[0]
            if node in graph.get(node, []):
                max_cycle_length = max(max_cycle_length, 1)
            continue

        # Build subgraph restricted to this SCC
        scc_set = set(scc)
        scc_graph: Graph = defaultdict(list)
        for node in scc:
            for neighbor in graph.get(node, []):
                if neighbor in scc_set:
                    scc_graph[node].append(neighbor)

        for start_node in scc:
            cycle_length = _dfs_find_cycle(scc_graph, start_node)
            max_cycle_length = max(max_cycle_length, cycle_length)

    return max_cycle_length


def build_graph(edges: list[Edge]) -> tuple[Graph, NodeSet]:
    """Build deduplicated adjacency list and node set from edges.

    Duplicate edges are removed to avoid redundant DFS work.

    Args:
        edges: List of directed edges.

    Returns:
        Tuple of (adjacency list graph, set of all nodes).
    """
    graph: Graph = defaultdict(list)
    nodes: NodeSet = set()
    seen: set[tuple[str, str]] = set()

    for edge in edges:
        nodes.add(edge.source)
        nodes.add(edge.destination)
        pair = (edge.source, edge.destination)
        if pair not in seen:
            seen.add(pair)
            graph[edge.source].append(edge.destination)

    return graph, nodes


def tarjan_sccs(graph: Graph, nodes: NodeSet) -> list[list[str]]:
    """Find all strongly connected components using iterative Tarjan's.

    Args:
        graph: Adjacency list representation of the graph.
        nodes: Set of all nodes in the graph.

    Returns:
        List of SCCs, each SCC being a list of node names.
    """
    index_map: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = 0

    for root in nodes:
        if root in index_map:
            continue

        index_map[root] = lowlink[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work: list[tuple[str, Iterator[str]]] = [(root, iter(graph.get(root, [])))]

        while work:
            node, neighbors = work[-1]
            advanced = False

            for neighbor in neighbors:
                if neighbor not in index_map:
                    index_map[neighbor] = lowlink[neighbor] = counter
                    counter += 1
                    stack.append(neighbor)
                    on_stack.add(neighbor)
                    work.append((neighbor, iter(graph.get(neighbor, []))))
                    advanced = True
                    break
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], index_map[neighbor])

            if not advanced:
                work.pop()

                if lowlink[node] == index_map[node]:
                    scc: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        scc.append(w)
                        if w == node:
                            break
                    sccs.append(scc)

                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[node])

    return sccs


def _dfs_find_cycle(graph: Graph, start_node: str) -> int:
    """DFS to find the longest cycle returning to start_node.

    Uses set for O(1) membership checks and in-place backtracking.

    Args:
        graph: Adjacency list representation of the graph.
        start_node: Node to start search from (and return to).

    Returns:
        Length of the longest cycle through start_node, or 0 if none.
    """
    max_cycle_length = 0
    visited: NodeSet = {start_node}

    def dfs(current: str, depth: int) -> None:
        nonlocal max_cycle_length
        for neighbor in graph[current]:
            if neighbor == start_node:
                max_cycle_length = max(max_cycle_length, depth)
            elif neighbor not in visited and depth < MAX_PATH_LENGTH:
                visited.add(neighbor)
                dfs(neighbor, depth + 1)
                visited.remove(neighbor)

    dfs(start_node, 1)
    return max_cycle_length
