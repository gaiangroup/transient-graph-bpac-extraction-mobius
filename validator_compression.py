"""AG-539 — Layer 5 compression rule validation.

Enforces Mobius PDF Section 8: every promotion upward must produce semantic
compression — fewer nodes, fewer edges, more meaning per object.

If Layer 5 node count >= Layer 4 node count → architecture violation.
"""

from db import get_session


def validate_compression(graph_name: str) -> dict:
    with get_session() as session:
        # Layer 4 counts — Episode, ResolvedEntity, MotifSequence, EpisodeWindow
        l4_nodes = session.run(
            """
            MATCH (n)
            WHERE (n:Episode OR n:ResolvedEntity OR n:MotifSequence OR n:EpisodeWindow
                   OR n:AttractorEpisodeType)
              AND n.graph_name = $graph_name
            RETURN count(n) AS cnt
            """,
            graph_name=graph_name,
        ).single()["cnt"]

        l4_edges = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE (a:Episode OR a:ResolvedEntity OR a:MotifSequence OR a:AttractorEpisodeType)
              AND a.graph_name = $graph_name
            RETURN count(r) AS cnt
            """,
            graph_name=graph_name,
        ).single()["cnt"]

        # Layer 5 counts — BEv, BE, BP, BL, BT
        l5_nodes = session.run(
            """
            MATCH (n)
            WHERE (n:BEv OR n:BE OR n:BP OR n:BL OR n:BT)
              AND n.graph_name = $graph_name
            RETURN count(n) AS cnt
            """,
            graph_name=graph_name,
        ).single()["cnt"]

        l5_edges = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE (a:BEv OR a:BE OR a:BP OR a:BL OR a:BT)
              AND a.graph_name = $graph_name
            RETURN count(r) AS cnt
            """,
            graph_name=graph_name,
        ).single()["cnt"]

    node_ratio = round(l5_nodes / l4_nodes, 4) if l4_nodes > 0 else 0
    edge_ratio = round(l5_edges / l4_edges, 4) if l4_edges > 0 else 0

    node_passes = l5_nodes < l4_nodes
    edge_passes = l5_edges < l4_edges

    passes = node_passes and edge_passes

    if passes:
        reduction = round((1 - node_ratio) * 100, 1)
        message = f"Layer 5 is {reduction}% smaller than Layer 4. Compression healthy."
    else:
        violations = []
        if not node_passes:
            violations.append(f"nodes: L5={l5_nodes} >= L4={l4_nodes}")
        if not edge_passes:
            violations.append(f"edges: L5={l5_edges} >= L4={l4_edges}")
        message = f"Architecture violation — {', '.join(violations)}"

    return {
        "graph_name":    graph_name,
        "layer4_nodes":  l4_nodes,
        "layer4_edges":  l4_edges,
        "layer5_nodes":  l5_nodes,
        "layer5_edges":  l5_edges,
        "node_ratio":    node_ratio,
        "edge_ratio":    edge_ratio,
        "passes":        passes,
        "message":       message,
    }
