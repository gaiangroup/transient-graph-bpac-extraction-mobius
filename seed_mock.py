"""Seed mock data into Neo4j Layer 5.

Replaces A1-A4 and C3 pipeline output for direct BE/BEv/BP/BL development and testing.

Seeds:
  - Episode nodes (CONFIRMED)      → consumed by BEv extractor (B2)
  - ResolvedEntity nodes            → consumed by BE extractor (B3)
  - MotifSequence nodes             → consumed by BP extractor (B4)
  - AttractorEpisodeType nodes      → consumed by BL extractor (AG-538)
"""

from db import get_session

GRAPH_NAME = "mobius_graph"

EPISODES = [
    # FRAUD_SEQUENCE cluster → maps to FRAUDULENT_COORDINATION BEv
    # user_alice initiates fraudulent transfers through user_bob targeting service_payments
    {
        "episode_id": "EP-001", "episode_type": "FRAUD_SEQUENCE", "status": "CONFIRMED",
        "first_seen": "2025-01-01T00:00:00", "last_seen": "2025-01-02T00:00:00",
        "initiator": "user_alice", "target": "service_payments",
        "actors": ["user_alice", "user_bob", "service_payments"],
        "amount": 15000.0,
        "description": "user_alice transfers 15000 through user_bob into service_payments in a structured fraud sequence",
    },
    {
        "episode_id": "EP-002", "episode_type": "FRAUD_SEQUENCE", "status": "CONFIRMED",
        "first_seen": "2025-01-03T00:00:00", "last_seen": "2025-01-04T00:00:00",
        "initiator": "user_alice", "target": "service_payments",
        "actors": ["user_alice", "user_bob", "service_payments"],
        "amount": 22000.0,
        "description": "Repeat fraud sequence — user_alice routes 22000 via user_bob to service_payments",
    },
    {
        "episode_id": "EP-003", "episode_type": "FRAUD_SEQUENCE", "status": "CONFIRMED",
        "first_seen": "2025-01-05T00:00:00", "last_seen": "2025-01-06T00:00:00",
        "initiator": "user_alice", "target": "service_payments",
        "actors": ["user_alice", "user_bob", "service_payments"],
        "amount": 18500.0,
        "description": "Third fraud sequence — same actors, same route, amount 18500",
    },
    # WASH_TRADING cluster → maps to CIRCULAR_VALUE_TRANSFER BEv
    # user_alice and user_bob circulate money back and forth with no real purpose
    {
        "episode_id": "EP-004", "episode_type": "WASH_TRADING", "status": "CONFIRMED",
        "first_seen": "2025-01-07T00:00:00", "last_seen": "2025-01-08T00:00:00",
        "initiator": "user_alice", "target": "user_alice",
        "actors": ["user_alice", "user_bob"],
        "amount": 5000.0,
        "description": "user_alice sends 5000 to user_bob, user_bob sends it back — circular with no net transfer",
    },
    {
        "episode_id": "EP-005", "episode_type": "WASH_TRADING", "status": "CONFIRMED",
        "first_seen": "2025-01-09T00:00:00", "last_seen": "2025-01-10T00:00:00",
        "initiator": "user_bob", "target": "user_bob",
        "actors": ["user_alice", "user_bob"],
        "amount": 8000.0,
        "description": "Same wash trading loop — 8000 circles between user_alice and user_bob again",
    },
    # COORDINATED_RATING → maps to COORDINATED_MANIPULATION BEv (only 1 — below min threshold)
    {
        "episode_id": "EP-006", "episode_type": "COORDINATED_RATING", "status": "CONFIRMED",
        "first_seen": "2025-01-11T00:00:00", "last_seen": "2025-01-12T00:00:00",
        "initiator": "user_alice", "target": "service_payments",
        "actors": ["user_alice", "user_bob", "service_payments"],
        "amount": 0.0,
        "description": "user_alice and user_bob simultaneously submit identical ratings to service_payments — coordinated manipulation",
    },
    # PENDING — not yet verified, should NOT be promoted
    {
        "episode_id": "EP-007", "episode_type": "FRAUD_SEQUENCE", "status": "PENDING",
        "first_seen": "2025-01-13T00:00:00", "last_seen": "2025-01-14T00:00:00",
        "initiator": "user_anon_1", "target": "service_payments",
        "actors": ["user_anon_1", "service_payments"],
        "amount": 3200.0,
        "description": "Suspected fraud by unknown actor user_anon_1 — under investigation, not yet confirmed",
    },
    # DATA_EXFILTRATION cluster → maps to UNAUTHORIZED_DATA_FLOW BEv
    # user_bob exfiltrates data from service_payments to external sink
    {
        "episode_id": "EP-008", "episode_type": "DATA_EXFILTRATION", "status": "CONFIRMED",
        "first_seen": "2025-01-15T00:00:00", "last_seen": "2025-01-16T00:00:00",
        "initiator": "user_bob", "target": "service_payments",
        "actors": ["user_bob", "service_payments"],
        "amount": 0.0,
        "description": "user_bob makes 47 rapid read calls to service_payments API — bulk data extraction pattern",
    },
    {
        "episode_id": "EP-009", "episode_type": "DATA_EXFILTRATION", "status": "CONFIRMED",
        "first_seen": "2025-01-17T00:00:00", "last_seen": "2025-01-18T00:00:00",
        "initiator": "user_bob", "target": "service_payments",
        "actors": ["user_bob", "service_payments"],
        "amount": 0.0,
        "description": "Second exfiltration attempt — user_bob accesses payment records outside business hours",
    },
    {
        "episode_id": "EP-010", "episode_type": "DATA_EXFILTRATION", "status": "CONFIRMED",
        "first_seen": "2025-01-19T00:00:00", "last_seen": "2025-01-20T00:00:00",
        "initiator": "user_bob", "target": "service_payments",
        "actors": ["user_bob", "service_payments"],
        "amount": 0.0,
        "description": "Third exfiltration — same pattern, user_bob exports full transaction history of service_payments",
    },
]

ENTITIES = [
    # Passes all 4 criteria → should promote to BE
    {
        "entity_id": "ENT-001", "canonical_id": "user_alice", "role": "INITIATOR",
        "identity_confidence": 0.95, "window_count": 5, "partition_count": 3, "episode_count": 4,
        "first_seen": "2025-01-01T00:00:00", "last_seen": "2025-01-20T00:00:00",
    },
    {
        "entity_id": "ENT-002", "canonical_id": "user_bob", "role": "INTERMEDIARY",
        "identity_confidence": 0.88, "window_count": 4, "partition_count": 2, "episode_count": 3,
        "first_seen": "2025-01-03T00:00:00", "last_seen": "2025-01-18T00:00:00",
    },
    {
        "entity_id": "ENT-003", "canonical_id": "service_payments", "role": "TARGET",
        "identity_confidence": 0.92, "window_count": 6, "partition_count": 4, "episode_count": 5,
        "first_seen": "2025-01-01T00:00:00", "last_seen": "2025-01-20T00:00:00",
    },
    # Fails confidence → should NOT promote
    {
        "entity_id": "ENT-004", "canonical_id": "user_anon_1", "role": "INITIATOR",
        "identity_confidence": 0.55, "window_count": 3, "partition_count": 2, "episode_count": 2,
        "first_seen": "2025-01-05T00:00:00", "last_seen": "2025-01-15T00:00:00",
    },
    # Fails window_count → should NOT promote
    {
        "entity_id": "ENT-005", "canonical_id": "user_temp", "role": "OBSERVER",
        "identity_confidence": 0.90, "window_count": 1, "partition_count": 2, "episode_count": 2,
        "first_seen": "2025-01-10T00:00:00", "last_seen": "2025-01-11T00:00:00",
    },
]

MOTIF_SEQUENCES = [
    # Stable FAN_OUT→TRIANGLE pattern repeated 6 times → should promote to BP
    {
        "seq_id": "SEQ-001", "pattern_signature": "FAN_OUT->TRIANGLE->CHAIN",
        "steps": ["FAN_OUT", "TRIANGLE", "CHAIN"],
        "episode_count": 3, "first_seen": "2025-01-01T00:00:00", "last_seen": "2025-01-10T00:00:00",
    },
    {
        "seq_id": "SEQ-002", "pattern_signature": "FAN_OUT->TRIANGLE->CHAIN",
        "steps": ["FAN_OUT", "TRIANGLE", "CHAIN"],
        "episode_count": 3, "first_seen": "2025-01-11T00:00:00", "last_seen": "2025-01-20T00:00:00",
    },
    # Unstable pattern (only 2 episodes) → should NOT promote
    {
        "seq_id": "SEQ-003", "pattern_signature": "CHAIN->CHAIN",
        "steps": ["CHAIN", "CHAIN"],
        "episode_count": 2, "first_seen": "2025-01-05T00:00:00", "last_seen": "2025-01-06T00:00:00",
    },
    # Another stable pattern
    {
        "seq_id": "SEQ-004", "pattern_signature": "FAN_OUT->FAN_OUT->TRIANGLE",
        "steps": ["FAN_OUT", "FAN_OUT", "TRIANGLE"],
        "episode_count": 3, "first_seen": "2025-01-02T00:00:00", "last_seen": "2025-01-08T00:00:00",
    },
    {
        "seq_id": "SEQ-005", "pattern_signature": "FAN_OUT->FAN_OUT->TRIANGLE",
        "steps": ["FAN_OUT", "FAN_OUT", "TRIANGLE"],
        "episode_count": 3, "first_seen": "2025-01-09T00:00:00", "last_seen": "2025-01-15T00:00:00",
    },
]


ATTRACTOR_TYPES = [
    # Passes all 4 criteria → should promote to BL
    {
        "type_id": "AT-001", "episode_type": "FRAUD_SEQUENCE",
        "attractor": True, "recurrence_score": 0.92, "epoch_count": 5,
        "affects_outcome": True,
        "source_episode_ids": ["EP-001", "EP-002", "EP-003"],
        "first_seen": "2025-01-01T00:00:00", "last_seen": "2025-01-20T00:00:00",
    },
    {
        "type_id": "AT-002", "episode_type": "WASH_TRADING",
        "attractor": True, "recurrence_score": 0.85, "epoch_count": 4,
        "affects_outcome": True,
        "source_episode_ids": ["EP-004", "EP-005"],
        "first_seen": "2025-01-07T00:00:00", "last_seen": "2025-01-10T00:00:00",
    },
    {
        "type_id": "AT-003", "episode_type": "DATA_EXFILTRATION",
        "attractor": True, "recurrence_score": 0.78, "epoch_count": 3,
        "affects_outcome": True,
        "source_episode_ids": ["EP-008", "EP-009", "EP-010"],
        "first_seen": "2025-01-15T00:00:00", "last_seen": "2025-01-20T00:00:00",
    },
    # Fails recurrence_score → should NOT promote
    {
        "type_id": "AT-004", "episode_type": "COORDINATED_RATING",
        "attractor": True, "recurrence_score": 0.45, "epoch_count": 4,
        "affects_outcome": True,
        "source_episode_ids": ["EP-006"],
        "first_seen": "2025-01-11T00:00:00", "last_seen": "2025-01-12T00:00:00",
    },
    # Fails attractor flag → should NOT promote
    {
        "type_id": "AT-005", "episode_type": "ANOMALY_SPIKE",
        "attractor": False, "recurrence_score": 0.80, "epoch_count": 3,
        "affects_outcome": True,
        "source_episode_ids": [],
        "first_seen": "2025-01-05T00:00:00", "last_seen": "2025-01-06T00:00:00",
    },
]


def seed(graph_name: str = GRAPH_NAME):
    with get_session() as session:
        # Clear existing mock data for this graph
        session.run("MATCH (e:Episode {graph_name: $g}) DETACH DELETE e",              g=graph_name)
        session.run("MATCH (r:ResolvedEntity {graph_name: $g}) DETACH DELETE r",       g=graph_name)
        session.run("MATCH (s:MotifSequence {graph_name: $g}) DETACH DELETE s",        g=graph_name)
        session.run("MATCH (a:AttractorEpisodeType {graph_name: $g}) DETACH DELETE a", g=graph_name)

        for ep in EPISODES:
            session.run(
                """
                CREATE (e:Episode {
                    episode_id:   $episode_id,
                    episode_type: $episode_type,
                    status:       $status,
                    first_seen:   $first_seen,
                    last_seen:    $last_seen,
                    initiator:    $initiator,
                    target:       $target,
                    actors:       $actors,
                    amount:       $amount,
                    description:  $description,
                    graph_name:   $graph_name
                })
                """,
                **ep, graph_name=graph_name,
            )

        for ent in ENTITIES:
            session.run(
                """
                CREATE (r:ResolvedEntity {
                    entity_id:          $entity_id,
                    canonical_id:       $canonical_id,
                    role:               $role,
                    identity_confidence: $identity_confidence,
                    window_count:       $window_count,
                    partition_count:    $partition_count,
                    episode_count:      $episode_count,
                    first_seen:         $first_seen,
                    last_seen:          $last_seen,
                    graph_name:         $graph_name
                })
                """,
                **ent, graph_name=graph_name,
            )

        for seq in MOTIF_SEQUENCES:
            session.run(
                """
                CREATE (s:MotifSequence {
                    seq_id:             $seq_id,
                    pattern_signature:  $pattern_signature,
                    steps:              $steps,
                    episode_count:      $episode_count,
                    first_seen:         $first_seen,
                    last_seen:          $last_seen,
                    graph_name:         $graph_name
                })
                """,
                **seq, graph_name=graph_name,
            )

        for att in ATTRACTOR_TYPES:
            session.run(
                """
                CREATE (a:AttractorEpisodeType {
                    type_id:             $type_id,
                    episode_type:        $episode_type,
                    attractor:           $attractor,
                    recurrence_score:    $recurrence_score,
                    epoch_count:         $epoch_count,
                    affects_outcome:     $affects_outcome,
                    source_episode_ids:  $source_episode_ids,
                    first_seen:          $first_seen,
                    last_seen:           $last_seen,
                    graph_name:          $graph_name
                })
                """,
                **att, graph_name=graph_name,
            )

    return {
        "episodes":  len(EPISODES),
        "entities":  len(ENTITIES),
        "sequences": len(MOTIF_SEQUENCES),
        "attractors": len(ATTRACTOR_TYPES),
        "graph_name": graph_name,
    }


if __name__ == "__main__":
    from schema import init_schema
    init_schema()
    result = seed()
    print("Seeded:", result)
