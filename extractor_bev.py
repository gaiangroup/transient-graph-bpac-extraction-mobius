"""B2 — Business Event (BEv) extraction.

Reads CONFIRMED Episode nodes → groups by archetype → promotes to BEv nodes.
Dependency stub: Episode nodes are seeded by seed_mock.py (replaces A3 output).
"""

import uuid
from db import get_session
from archetype_map import episode_type_to_archetype
from models import ExtractBEvRequest, ExtractionResult
from promotion_scorer import score_bev, write_review_queue


def extract_bevs(req: ExtractBEvRequest) -> ExtractionResult:
    with get_session() as session:
        # 1. Fetch all CONFIRMED episodes for this graph
        result = session.run(
            """
            MATCH (e:Episode {graph_name: $graph_name, status: 'CONFIRMED'})
            RETURN e.episode_id   AS episode_id,
                   e.episode_type AS episode_type,
                   e.first_seen   AS first_seen,
                   e.last_seen    AS last_seen
            ORDER BY e.episode_type
            """,
            graph_name=req.graph_name,
        )
        episodes = [dict(r) for r in result]

    if not episodes:
        return ExtractionResult(promoted=0, skipped=0, nodes=[])

    # 2. Group by archetype
    groups: dict[str, list] = {}
    for ep in episodes:
        archetype = episode_type_to_archetype(ep["episode_type"])
        groups.setdefault(archetype, []).append(ep)

    promoted_nodes = []
    skipped = 0

    with get_session() as session:
        for archetype, eps in groups.items():
            if len(eps) < req.min_episode_count:
                skipped += len(eps)
                continue

            source_ids = [e["episode_id"] for e in eps]
            score = score_bev(archetype, len(eps), source_ids, req.graph_name)

            bev_id = f"BEv-{archetype}-{req.graph_name}-{uuid.uuid4().hex[:8]}"

            if score["decision"] == "REVIEW":
                write_review_queue(bev_id, "BEv", score["promotion_score"],
                                   score["checklist_scores"], req.graph_name)
                skipped += len(eps)
                continue
            if score["decision"] == "SKIP":
                skipped += len(eps)
                continue

            first_seen = min(e["first_seen"] for e in eps if e["first_seen"])
            last_seen  = max(e["last_seen"]  for e in eps if e["last_seen"])

            # 3. Merge BEv node
            session.run(
                """
                MERGE (b:BEv {bev_id: $bev_id})
                SET b.archetype          = $archetype,
                    b.graph_name         = $graph_name,
                    b.first_seen         = $first_seen,
                    b.last_seen          = $last_seen,
                    b.recurrence_count   = $recurrence_count,
                    b.source_episode_ids = $source_ids,
                    b.promotion_score    = $promotion_score,
                    b.checklist_scores   = $checklist_scores,
                    b.promoted_at        = datetime()
                """,
                bev_id=bev_id,
                archetype=archetype,
                graph_name=req.graph_name,
                first_seen=first_seen,
                last_seen=last_seen,
                recurrence_count=len(eps),
                source_ids=source_ids,
                promotion_score=score["promotion_score"],
                checklist_scores=str(score["checklist_scores"]),
            )

            # 4. Link each source episode → BEv
            for ep in eps:
                session.run(
                    """
                    MATCH (e:Episode {episode_id: $episode_id})
                    MATCH (b:BEv     {bev_id:     $bev_id})
                    MERGE (e)-[:PROMOTED_TO]->(b)
                    """,
                    episode_id=ep["episode_id"],
                    bev_id=bev_id,
                )

            promoted_nodes.append({
                "bev_id":             bev_id,
                "archetype":          archetype,
                "source_episode_ids": source_ids,
                "first_seen":         first_seen,
                "last_seen":          last_seen,
                "graph_name":         req.graph_name,
                "recurrence_count":   len(eps),
                "promotion_score":    score["promotion_score"],
                "checklist_scores":   score["checklist_scores"],
            })

    return ExtractionResult(
        promoted=len(promoted_nodes),
        skipped=skipped,
        nodes=promoted_nodes,
    )
