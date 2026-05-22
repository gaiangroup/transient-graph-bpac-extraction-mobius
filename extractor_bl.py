"""AG-538 — Business Law (BL) extraction.

Reads attractor-flagged episode types from Layer 4 → checks 4 PDF Section 4
Coupling/Constraint/Control criteria → promotes to BL nodes in Layer 5.

Promotion criteria (all must pass):
  1. attractor == True            (attractor or control surface inferred)
  2. recurrence_score >= threshold (policy/law relationship is stable)
  3. epoch_count >= min_epochs    (repeated dependency observed across epochs)
  4. affects_outcome == True      (binding constraint affects outcomes)
"""

import uuid
from db import get_session
from models import ExtractBLRequest, ExtractionResult
from promotion_scorer import score_bl, write_review_queue


def extract_bls(req: ExtractBLRequest) -> ExtractionResult:
    with get_session() as session:
        result = session.run(
            """
            MATCH (a:AttractorEpisodeType {graph_name: $graph_name})
            RETURN a.type_id          AS type_id,
                   a.episode_type     AS episode_type,
                   a.attractor        AS attractor,
                   a.recurrence_score AS recurrence_score,
                   a.epoch_count      AS epoch_count,
                   a.affects_outcome  AS affects_outcome,
                   a.first_seen       AS first_seen,
                   a.last_seen        AS last_seen,
                   a.source_episode_ids AS source_episode_ids
            """,
            graph_name=req.graph_name,
        )
        attractors = [dict(r) for r in result]

    if not attractors:
        return ExtractionResult(promoted=0, skipped=0, nodes=[])

    promoted_nodes = []
    skipped = 0

    with get_session() as session:
        for a in attractors:
            is_attractor     = a.get("attractor") or False
            recurrence       = a.get("recurrence_score") or 0.0
            epoch_count      = a.get("epoch_count") or 0
            affects_outcome  = a.get("affects_outcome") or False

            if (not is_attractor or
                recurrence < req.min_recurrence_score or
                epoch_count < req.min_epochs or
                not affects_outcome):
                skipped += 1
                continue

            score = score_bl(recurrence, epoch_count, a.get("episode_type") or "")
            bl_id = f"BL-{req.graph_name}-{uuid.uuid4().hex[:8]}"

            if score["decision"] == "REVIEW":
                write_review_queue(bl_id, "BL", score["promotion_score"],
                                   score["checklist_scores"], req.graph_name)
                skipped += 1
                continue
            if score["decision"] == "SKIP":
                skipped += 1
                continue

            session.run(
                """
                MERGE (b:BL {bl_id: $bl_id})
                SET b.episode_type     = $episode_type,
                    b.recurrence_score = $recurrence_score,
                    b.epoch_count      = $epoch_count,
                    b.first_seen       = $first_seen,
                    b.last_seen        = $last_seen,
                    b.graph_name       = $graph_name,
                    b.promotion_score  = $promotion_score,
                    b.checklist_scores = $checklist_scores,
                    b.promoted_at      = datetime()
                """,
                bl_id=bl_id,
                episode_type=a["episode_type"],
                recurrence_score=recurrence,
                epoch_count=epoch_count,
                first_seen=a.get("first_seen"),
                last_seen=a.get("last_seen"),
                graph_name=req.graph_name,
                promotion_score=score["promotion_score"],
                checklist_scores=str(score["checklist_scores"]),
            )

            # Link source attractor → BL
            session.run(
                """
                MATCH (a:AttractorEpisodeType {type_id: $type_id})
                MATCH (b:BL {bl_id: $bl_id})
                MERGE (a)-[:PROMOTED_TO]->(b)
                """,
                type_id=a["type_id"],
                bl_id=bl_id,
            )

            # Create BT trace node
            bt_id = f"BT-{bl_id}"
            session.run(
                """
                MERGE (t:BT {bt_id: $bt_id})
                SET t.source_node_id   = $bl_id,
                    t.source_type      = 'BL',
                    t.source_episode_ids = $source_ids,
                    t.graph_name       = $graph_name,
                    t.created_at       = datetime()
                WITH t
                MATCH (b:BL {bl_id: $bl_id})
                MERGE (b)-[:HAS_TRACE]->(t)
                """,
                bt_id=bt_id,
                bl_id=bl_id,
                source_ids=a.get("source_episode_ids") or [],
                graph_name=req.graph_name,
            )

            promoted_nodes.append({
                "bl_id":            bl_id,
                "episode_type":     a["episode_type"],
                "recurrence_score": recurrence,
                "epoch_count":      epoch_count,
                "first_seen":       a.get("first_seen"),
                "last_seen":        a.get("last_seen"),
                "graph_name":       req.graph_name,
                "promotion_score":  score["promotion_score"],
                "checklist_scores": score["checklist_scores"],
            })

    return ExtractionResult(
        promoted=len(promoted_nodes),
        skipped=skipped,
        nodes=promoted_nodes,
    )
