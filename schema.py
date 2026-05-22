"""B1 — Layer 5 durable Neo4j schema.

Run once via /admin/init-schema or at startup.
Creates constraints + indexes for BE, BEv, BP, BT node types.
"""

from db import get_session

CONSTRAINTS = [
    # uniqueness
    "CREATE CONSTRAINT be_id IF NOT EXISTS FOR (n:BE) REQUIRE n.be_id IS UNIQUE",
    "CREATE CONSTRAINT bev_id IF NOT EXISTS FOR (n:BEv) REQUIRE n.bev_id IS UNIQUE",
    "CREATE CONSTRAINT bp_id IF NOT EXISTS FOR (n:BP) REQUIRE n.bp_id IS UNIQUE",
    "CREATE CONSTRAINT bt_id IF NOT EXISTS FOR (n:BT) REQUIRE n.bt_id IS UNIQUE",
    "CREATE CONSTRAINT bl_id IF NOT EXISTS FOR (n:BL) REQUIRE n.bl_id IS UNIQUE",
    "CREATE CONSTRAINT attractor_type_id IF NOT EXISTS FOR (n:AttractorEpisodeType) REQUIRE n.type_id IS UNIQUE",
    # episode nodes (seeded mock / produced by A-group)
    "CREATE CONSTRAINT episode_id IF NOT EXISTS FOR (n:Episode) REQUIRE n.episode_id IS UNIQUE",
    # resolved entities (seeded mock / produced by A4)
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:ResolvedEntity) REQUIRE n.entity_id IS UNIQUE",
    # motif sequences (seeded mock / produced by A2)
    "CREATE CONSTRAINT seq_id IF NOT EXISTS FOR (n:MotifSequence) REQUIRE n.seq_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX episode_type IF NOT EXISTS FOR (n:Episode) ON (n.episode_type)",
    "CREATE INDEX episode_status IF NOT EXISTS FOR (n:Episode) ON (n.status)",
    "CREATE INDEX episode_graph IF NOT EXISTS FOR (n:Episode) ON (n.graph_name)",
    "CREATE INDEX entity_graph IF NOT EXISTS FOR (n:ResolvedEntity) ON (n.graph_name)",
    "CREATE INDEX entity_role IF NOT EXISTS FOR (n:ResolvedEntity) ON (n.role)",
    "CREATE INDEX seq_graph IF NOT EXISTS FOR (n:MotifSequence) ON (n.graph_name)",
    "CREATE INDEX bev_archetype IF NOT EXISTS FOR (n:BEv) ON (n.archetype)",
    "CREATE INDEX be_graph IF NOT EXISTS FOR (n:BE) ON (n.graph_name)",
    "CREATE INDEX bp_graph IF NOT EXISTS FOR (n:BP) ON (n.graph_name)",
    "CREATE INDEX bl_graph IF NOT EXISTS FOR (n:BL) ON (n.graph_name)",
    "CREATE INDEX attractor_graph IF NOT EXISTS FOR (n:AttractorEpisodeType) ON (n.graph_name)",
    "CREATE INDEX review_queue_graph IF NOT EXISTS FOR (n:ReviewQueueItem) ON (n.graph_name)",
]


def init_schema():
    with get_session() as session:
        for stmt in CONSTRAINTS + INDEXES:
            session.run(stmt)
    return {"status": "ok", "applied": len(CONSTRAINTS) + len(INDEXES)}
