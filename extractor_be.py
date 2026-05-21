"""B3 — Business Entity (BE) extraction.

Reads ResolvedEntity nodes → checks 4 promotion criteria → writes BE nodes.
Dependency stub: ResolvedEntity nodes seeded by seed_mock.py (replaces A4 output).

Promotion criteria (all must pass):
  1. identity_confidence >= min_confidence
  2. window_count >= min_windows        (role persists across N time windows)
  3. partition_count >= min_partitions  (survives N partitions)
  4. episode_count >= min_episodes      (appears in N episodes)
"""

import uuid
from db import get_session
from models import ExtractBERequest, ExtractionResult


def extract_bes(req: ExtractBERequest) -> ExtractionResult:
    with get_session() as session:
        result = session.run(
            """
            MATCH (r:ResolvedEntity {graph_name: $graph_name})
            RETURN r.entity_id          AS entity_id,
                   r.canonical_id       AS canonical_id,
                   r.role               AS role,
                   r.identity_confidence AS confidence,
                   r.window_count       AS window_count,
                   r.partition_count    AS partition_count,
                   r.episode_count      AS episode_count,
                   r.first_seen         AS first_seen,
                   r.last_seen          AS last_seen
            """,
            graph_name=req.graph_name,
        )
        entities = [dict(r) for r in result]

    if not entities:
        return ExtractionResult(promoted=0, skipped=0, nodes=[])

    promoted_nodes = []
    skipped = 0

    with get_session() as session:
        for ent in entities:
            conf      = ent.get("confidence") or 0.0
            windows   = ent.get("window_count") or 0
            parts     = ent.get("partition_count") or 0
            eps       = ent.get("episode_count") or 0

            if (conf < req.min_confidence or
                windows < req.min_windows or
                parts < req.min_partitions or
                eps < req.min_episodes):
                skipped += 1
                continue

            be_id = f"BE-{req.graph_name}-{uuid.uuid4().hex[:8]}"

            session.run(
                """
                MERGE (b:BE {be_id: $be_id})
                SET b.canonical_id    = $canonical_id,
                    b.role            = $role,
                    b.confidence      = $confidence,
                    b.partition_count = $partition_count,
                    b.episode_count   = $episode_count,
                    b.first_seen      = $first_seen,
                    b.last_seen       = $last_seen,
                    b.graph_name      = $graph_name,
                    b.promoted_at     = datetime()
                """,
                be_id=be_id,
                canonical_id=ent["canonical_id"],
                role=ent["role"],
                confidence=conf,
                partition_count=parts,
                episode_count=eps,
                first_seen=ent.get("first_seen"),
                last_seen=ent.get("last_seen"),
                graph_name=req.graph_name,
            )

            # Link source ResolvedEntity → BE
            session.run(
                """
                MATCH (r:ResolvedEntity {entity_id: $entity_id})
                MATCH (b:BE {be_id: $be_id})
                MERGE (r)-[:PROMOTED_TO]->(b)
                """,
                entity_id=ent["entity_id"],
                be_id=be_id,
            )

            promoted_nodes.append({
                "be_id":          be_id,
                "canonical_id":   ent["canonical_id"],
                "role":           ent["role"],
                "confidence":     conf,
                "partition_count": parts,
                "episode_count":  eps,
                "first_seen":     ent.get("first_seen"),
                "last_seen":      ent.get("last_seen"),
                "graph_name":     req.graph_name,
            })

    return ExtractionResult(
        promoted=len(promoted_nodes),
        skipped=skipped,
        nodes=promoted_nodes,
    )
