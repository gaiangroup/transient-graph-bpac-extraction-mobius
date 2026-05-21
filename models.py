from pydantic import BaseModel
from typing import Any, Dict, List, Optional


# ── Inputs ────────────────────────────────────────────────────────────────────

class ExtractBEvRequest(BaseModel):
    graph_name: str
    min_episode_count: int = 1          # promote BEv if backed by ≥ N episodes


class ExtractBERequest(BaseModel):
    graph_name: str
    min_confidence: float = 0.8         # identity resolution threshold
    min_windows: int = 3                # role must persist across N time windows
    min_partitions: int = 2             # must appear in N partitions
    min_episodes: int = 2               # must participate in N episodes


class ExtractBPRequest(BaseModel):
    graph_name: str
    min_episodes: int = 5               # workflow must repeat ≥ N times
    transition_stability_threshold: float = 0.6  # transition prob must be ≥ this


# ── Outputs ───────────────────────────────────────────────────────────────────

class BEvNode(BaseModel):
    bev_id: str
    archetype: str
    source_episode_ids: List[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
    graph_name: str
    recurrence_count: int


class BENode(BaseModel):
    be_id: str
    canonical_id: str
    role: str
    confidence: float
    partition_count: int
    episode_count: int
    first_seen: Optional[str]
    last_seen: Optional[str]
    graph_name: str


class BPNode(BaseModel):
    bp_id: str
    pattern_signature: str
    episode_count: int
    transition_probabilities: Dict[str, float]
    first_seen: Optional[str]
    last_seen: Optional[str]
    graph_name: str


class ExtractionResult(BaseModel):
    promoted: int
    skipped: int
    nodes: List[Dict[str, Any]]
