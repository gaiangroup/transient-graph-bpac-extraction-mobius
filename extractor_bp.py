"""B4 — Business Process (BP) extraction.

Reads MotifSequence nodes → computes transition probabilities →
promotes stable, recurring workflow patterns to BP nodes.

Dependency stub: MotifSequence nodes seeded by seed_mock.py (replaces A2 output).

Promotion criteria:
  1. episode_count >= min_episodes           (workflow repeats ≥ N times)
  2. all transition probabilities >= threshold  (pattern is stable)
"""

import uuid
import json
from collections import Counter
from db import get_session
from models import ExtractBPRequest, ExtractionResult
from promotion_scorer import score_bp, write_review_queue


def _compute_transitions(sequences: list[dict]) -> dict[str, float]:
    """
    Each sequence has a `steps` field — ordered list of motif type strings.
    Compute P(next_step | current_step) across all sequences.
    Returns dict like {"FAN_OUT->TRIANGLE": 0.75, ...}
    """
    pair_counts: Counter = Counter()
    from_counts: Counter = Counter()

    for seq in sequences:
        steps = seq.get("steps") or []
        for i in range(len(steps) - 1):
            pair_counts[(steps[i], steps[i + 1])] += 1
            from_counts[steps[i]] += 1

    transitions = {}
    for (src, tgt), count in pair_counts.items():
        key = f"{src}->{tgt}"
        transitions[key] = round(count / from_counts[src], 4)

    return transitions


def extract_bps(req: ExtractBPRequest) -> ExtractionResult:
    with get_session() as session:
        result = session.run(
            """
            MATCH (s:MotifSequence {graph_name: $graph_name})
            RETURN s.seq_id           AS seq_id,
                   s.pattern_signature AS pattern_signature,
                   s.steps            AS steps,
                   s.episode_count    AS episode_count,
                   s.first_seen       AS first_seen,
                   s.last_seen        AS last_seen
            """,
            graph_name=req.graph_name,
        )
        sequences = [dict(r) for r in result]

    if not sequences:
        return ExtractionResult(promoted=0, skipped=0, nodes=[])

    # Group by pattern_signature
    groups: dict[str, list] = {}
    for seq in sequences:
        sig = seq.get("pattern_signature") or "UNKNOWN"
        groups.setdefault(sig, []).append(seq)

    promoted_nodes = []
    skipped = 0

    with get_session() as session:
        for sig, seqs in groups.items():
            total_episodes = sum(s.get("episode_count") or 1 for s in seqs)

            if total_episodes < req.min_episodes:
                skipped += len(seqs)
                continue

            transitions = _compute_transitions(seqs)

            if transitions and min(transitions.values()) < req.transition_stability_threshold:
                skipped += len(seqs)
                continue

            score = score_bp(total_episodes, transitions, sig)
            bp_id = f"BP-{req.graph_name}-{uuid.uuid4().hex[:8]}"

            if score["decision"] == "REVIEW":
                write_review_queue(bp_id, "BP", score["promotion_score"],
                                   score["checklist_scores"], req.graph_name)
                skipped += len(seqs)
                continue
            if score["decision"] == "SKIP":
                skipped += len(seqs)
                continue

            first_seen = min(s["first_seen"] for s in seqs if s.get("first_seen"))
            last_seen  = max(s["last_seen"]  for s in seqs if s.get("last_seen"))

            session.run(
                """
                MERGE (b:BP {bp_id: $bp_id})
                SET b.pattern_signature        = $pattern_signature,
                    b.episode_count            = $episode_count,
                    b.transition_probabilities = $transitions,
                    b.first_seen               = $first_seen,
                    b.last_seen                = $last_seen,
                    b.graph_name               = $graph_name,
                    b.promotion_score          = $promotion_score,
                    b.checklist_scores         = $checklist_scores,
                    b.promoted_at              = datetime()
                """,
                bp_id=bp_id,
                pattern_signature=sig,
                episode_count=total_episodes,
                transitions=json.dumps(transitions),
                first_seen=first_seen,
                last_seen=last_seen,
                graph_name=req.graph_name,
                promotion_score=score["promotion_score"],
                checklist_scores=str(score["checklist_scores"]),
            )

            for seq in seqs:
                session.run(
                    """
                    MATCH (s:MotifSequence {seq_id: $seq_id})
                    MATCH (b:BP {bp_id: $bp_id})
                    MERGE (s)-[:PROMOTED_TO]->(b)
                    """,
                    seq_id=seq["seq_id"],
                    bp_id=bp_id,
                )

            promoted_nodes.append({
                "bp_id":                   bp_id,
                "pattern_signature":       sig,
                "episode_count":           total_episodes,
                "transition_probabilities": transitions,
                "first_seen":              first_seen,
                "last_seen":               last_seen,
                "graph_name":              req.graph_name,
                "promotion_score":         score["promotion_score"],
                "checklist_scores":        score["checklist_scores"],
            })

    return ExtractionResult(
        promoted=len(promoted_nodes),
        skipped=skipped,
        nodes=promoted_nodes,
    )
