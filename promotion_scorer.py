"""AG-540 — PDF Section 10 five-question promotion gate.

Shared scorer used by BEv, BE, BP, BL extractors.
Every promoted node gets promotion_score (0-5) and checklist_scores (JSON).

5 questions (Mobius PDF Section 10):
  Q1 — Stable enough?          recurrence / episode count above threshold
  Q2 — Semantically meaningful? has valid archetype / role / pattern
  Q3 — Reusable across analyses? appears in multiple partitions / windows
  Q4 — Affects BR/BM/BL/BP?    connected to broader business impact
  Q5 — Losing it damages long-horizon reasoning? has trace / provenance

Score:
  5/5 → auto-promote
  3-4/5 → add to review queue, do NOT promote
  0-2/5 → skip
"""

from db import get_session


REVIEW_THRESHOLD = 3
AUTO_THRESHOLD   = 5


def score_bev(archetype: str, recurrence_count: int, source_episode_ids: list,
              graph_name: str) -> dict:
    scores = {
        "Q1_stable":      recurrence_count >= 2,
        "Q2_meaningful":  archetype not in ("ANOMALOUS_EVENT", "UNKNOWN", ""),
        "Q3_reusable":    len(source_episode_ids) >= 2,
        "Q4_affects_bpac": True,  # BEv by definition feeds BP — always affects BPAC
        "Q5_long_horizon": recurrence_count >= 3,
    }
    return _build_result(scores)


def score_be(confidence: float, window_count: int, partition_count: int,
             episode_count: int, role: str) -> dict:
    scores = {
        "Q1_stable":      episode_count >= 2,
        "Q2_meaningful":  role not in ("UNKNOWN", "", None),
        "Q3_reusable":    partition_count >= 2 and window_count >= 3,
        "Q4_affects_bpac": confidence >= 0.8,
        "Q5_long_horizon": window_count >= 3,
    }
    return _build_result(scores)


def score_bp(episode_count: int, transitions: dict, pattern_signature: str) -> dict:
    min_transition = min(transitions.values()) if transitions else 0.0
    scores = {
        "Q1_stable":      episode_count >= 5,
        "Q2_meaningful":  pattern_signature not in ("UNKNOWN", "", None),
        "Q3_reusable":    episode_count >= 5,
        "Q4_affects_bpac": True,  # BP is a process — always BPAC-relevant
        "Q5_long_horizon": min_transition >= 0.6,
    }
    return _build_result(scores)


def score_bl(recurrence_score: float, epoch_count: int, episode_type: str) -> dict:
    scores = {
        "Q1_stable":      recurrence_score >= 0.7,
        "Q2_meaningful":  episode_type not in ("UNKNOWN", "", None),
        "Q3_reusable":    epoch_count >= 3,
        "Q4_affects_bpac": True,  # BL is a law — always constrains BPAC
        "Q5_long_horizon": recurrence_score >= 0.7 and epoch_count >= 3,
    }
    return _build_result(scores)


def _build_result(scores: dict) -> dict:
    total = sum(1 for v in scores.values() if v)
    if total == AUTO_THRESHOLD:
        decision = "PROMOTE"
    elif total >= REVIEW_THRESHOLD:
        decision = "REVIEW"
    else:
        decision = "SKIP"

    return {
        "promotion_score":   total,
        "checklist_scores":  {k: int(v) for k, v in scores.items()},
        "decision":          decision,
    }


def write_review_queue(node_id: str, node_type: str, promotion_score: int,
                       checklist_scores: dict, graph_name: str):
    with get_session() as session:
        session.run(
            """
            MERGE (q:ReviewQueueItem {node_id: $node_id})
            SET q.node_type        = $node_type,
                q.promotion_score  = $promotion_score,
                q.checklist_scores = $checklist_scores,
                q.graph_name       = $graph_name,
                q.queued_at        = datetime(),
                q.status           = 'PENDING_REVIEW'
            """,
            node_id=node_id,
            node_type=node_type,
            promotion_score=promotion_score,
            checklist_scores=str(checklist_scores),
            graph_name=graph_name,
        )
