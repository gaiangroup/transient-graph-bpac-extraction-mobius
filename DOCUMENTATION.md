# BPAC Extraction Service — Documentation

## Index

1. [What is this service?](#1-what-is-this-service)
2. [Where does it fit in the 5-layer architecture?](#2-where-does-it-fit-in-the-5-layer-architecture)
3. [What are BEv, BE, and BP?](#3-what-are-bev-be-and-bp)
4. [How does promotion work?](#4-how-does-promotion-work)
5. [Project structure](#5-project-structure)
6. [How to run locally](#6-how-to-run-locally)
7. [API endpoints](#7-api-endpoints)
8. [Test cases](#8-test-cases)
9. [Mock seed data](#9-mock-seed-data)
10. [Dependency chain](#10-dependency-chain)
11. [Archetype mapping table](#11-archetype-mapping-table)

---

## 1. What is this service?

This service implements **Layer 5** of the Mobius graph pipeline — the **Canonical Durable Graph**.

Its job is to look at the episodic data accumulated in Layer 4, apply promotion rules, and write only the **stable, meaningful, recurring structures** into a long-term Neo4j graph.

The core principle from the Mobius PDF:
> *"Raw events should flow through graphs; only stable structure should live in graphs durably."*

This service is the final gate. It decides what deserves to exist permanently.

---

## 2. Where does it fit in the 5-layer architecture?

```
Layer 1 — Raw event substrate
         (columnar store, lakehouse, log store)
              ↓
Layer 2 — Ephemeral interaction graph
         (Redis + FalkorDB, TTL-based, expiring)
              ↓
Layer 3 — Pattern extraction graph        ← motif-detection service
         (motifs, anomalous subgraphs, FAN_OUT / TRIANGLE / CHAIN)
              ↓
Layer 4 — Episodic / accumulation graph   ← feeds INTO this service
         (Neo4j: CONFIRMED episodes, resolved entities, motif sequences)
              ↓
Layer 5 — Canonical durable graph         ← THIS SERVICE
         (Neo4j: BEv nodes, BE nodes, BP nodes)
```

**Why two Neo4j instances?**
- Layer 4 (port 7687) is semi-durable — it holds provisional structures with confidence scores that can change.
- Layer 5 (port 7688) is durable — once something is written here, it is a certified stable structure.

---

## 3. What are BEv, BE, and BP?

These are the three types of structures this service extracts and promotes.

### Business Event (BEv)
**What it is:** A recurring type of suspicious or notable event that keeps happening across the graph.

**Simple example:** If "fraud sequences" keep appearing again and again across different marketplaces and time windows, that pattern of fraud is promoted as a named Business Event: `FRAUDULENT_COORDINATION`.

**What it is NOT:** A single fraud incident. One fraud is just an episode. BEv means this type of fraud is a recognized, recurring pattern.

**Source:** CONFIRMED Episode nodes from Layer 4.

**Promoted when:** The same episode type appears in enough confirmed episodes (threshold configurable, default ≥ 1 per archetype group).

---

### Business Entity (BE)
**What it is:** A real-world actor (person, system, service) that is stable, confirmed, and strategically important enough to exist permanently in the graph.

**Simple example:** `user_alice` appears in 4 episodes, across 3 partitions, over 5 time windows, and her identity is 95% confirmed. She is a persistent actor — not noise. She gets promoted as a BE node.

**What it is NOT:** Any node that appeared once or twice. BE is earned through consistency.

**Source:** ResolvedEntity nodes from Layer 4 (identity resolution output).

**Promoted when all 4 criteria pass (from Mobius PDF Section 4):**
1. `identity_confidence >= 0.8` — we are sure this is a real, unique entity
2. `window_count >= 3` — role persists across multiple time windows
3. `partition_count >= 2` — appears in multiple graph partitions (not just local noise)
4. `episode_count >= 2` — participated in multiple episodes (matters strategically)

---

### Business Process (BP)
**What it is:** A repeating workflow — a sequence of motif patterns that consistently happens in the same order across many episodes.

**Simple example:** Every time fraud happens, the graph shows `FAN_OUT → TRIANGLE → CHAIN` in that order. This pattern happens 6 times. The transitions are 100% stable. This is a recognized process: it has a name, a signature, and transition probabilities.

**What it is NOT:** A workflow seen only once or twice, or one where the next step is random.

**Source:** MotifSequence nodes from Layer 4 (episode assembler output).

**Promoted when:**
1. Pattern repeats in `>= 5` episodes (configurable)
2. All transition probabilities `>= 0.6` (stable — not random)

---

## 4. How does promotion work?

The Mobius PDF (Section 10) defines a 5-question gate for promoting anything to the durable graph:

| Question | What it checks |
|----------|---------------|
| Is it stable enough? | Recurrence count above threshold |
| Is it semantically meaningful? | Has a valid BPAC archetype mapping |
| Is it reusable across analyses? | Appears in multiple partitions/windows |
| Does it affect BR, BM, BL, or BP structure? | Connected to broader business impact |
| Would losing it damage long-horizon reasoning? | Provenance and trace anchoring matters |

This service implements these gates as concrete numeric thresholds for BEv, BE, and BP. The B5 Promotion Engine (AG-531) adds the D* deontic backing check on top.

**Flow:**
```
Layer 4 Neo4j
    ↓  read CONFIRMED Episodes
    ↓  read ResolvedEntity nodes
    ↓  read MotifSequence nodes
         ↓
    Apply promotion criteria
         ↓
    Write BEv / BE / BP nodes to Layer 5 Neo4j
    Create PROMOTED_TO / PARTICIPATES_IN edges
    Create BT (Trace) node linking back to source
```

---

## 5. Project structure

```
bpac-extraction/
├── main.py           — FastAPI app, all endpoints, startup schema init
├── models.py         — Pydantic request/response models
├── db.py             — Neo4j driver connection (Layer 5, port 7688)
├── schema.py         — B1: Layer 5 Neo4j constraints + indexes
├── archetype_map.py  — Episode type → BEv archetype mapping table
├── extractor_bev.py  — B2: BEv extraction logic
├── extractor_be.py   — B3: BE extraction logic
├── extractor_bp.py   — B4: BP extraction logic
├── seed_mock.py      — Mock data seeder (replaces A1-A4 pipeline output)
├── test_cases.json   — Test inputs and expected outputs for all 3 extractors
├── requirements.txt  — Python dependencies
└── .env              — Neo4j connection config (not committed)
```

---

## 6. How to run locally

**Prerequisites:**
- Python 3.10+
- Docker (for Neo4j)

**Step 1 — Start Neo4j Layer 5:**
```bash
docker run -d --name neo4j-l5 \
  -p 7475:7474 -p 7688:7687 \
  -e NEO4J_AUTH=neo4j/gaian@12345 \
  neo4j:5.20
```

**Step 2 — Create virtual environment:**
```bash
cd bpac-extraction
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**Step 3 — Configure `.env`:**
```
NEO4J_URI=bolt://localhost:7688
NEO4J_USER=neo4j
NEO4J_PASSWORD=gaian@12345
```

**Step 4 — Seed mock data (replaces A1-A4 pipeline):**
```bash
venv/bin/python seed_mock.py
```

**Step 5 — Start the service:**
```bash
venv/bin/uvicorn main:app --port 8702 --reload
```

**Step 6 — Open Swagger docs:**
```
http://localhost:8702/docs
```

---

## 7. API endpoints

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/init-schema` | Apply Layer 5 Neo4j constraints and indexes |
| POST | `/admin/seed-mock?graph_name=mobius_graph` | Seed mock episodes, entities, sequences |

---

### B2 — Business Event Extraction

**`POST /api/v1/mobius/layer5/extract/events`**

Request:
```json
{
  "graph_name": "mobius_graph",
  "min_episode_count": 1
}
```

Response:
```json
{
  "promoted": 4,
  "skipped": 0,
  "nodes": [
    {
      "bev_id": "BEv-FRAUDULENT_COORDINATION-mobius_graph-abc123",
      "archetype": "FRAUDULENT_COORDINATION",
      "source_episode_ids": ["EP-001", "EP-002", "EP-003"],
      "first_seen": "2025-01-01T00:00:00",
      "last_seen": "2025-01-06T00:00:00",
      "graph_name": "mobius_graph",
      "recurrence_count": 3
    }
  ]
}
```

---

### B3 — Business Entity Extraction

**`POST /api/v1/mobius/layer5/extract/entities`**

Request:
```json
{
  "graph_name": "mobius_graph",
  "min_confidence": 0.8,
  "min_windows": 3,
  "min_partitions": 2,
  "min_episodes": 2
}
```

Response:
```json
{
  "promoted": 3,
  "skipped": 2,
  "nodes": [
    {
      "be_id": "BE-mobius_graph-fe6e64d7",
      "canonical_id": "user_alice",
      "role": "INITIATOR",
      "confidence": 0.95,
      "partition_count": 3,
      "episode_count": 4,
      "first_seen": "2025-01-01T00:00:00",
      "last_seen": "2025-01-20T00:00:00",
      "graph_name": "mobius_graph"
    }
  ]
}
```

---

### B4 — Business Process Extraction

**`POST /api/v1/mobius/layer5/extract/processes`**

Request:
```json
{
  "graph_name": "mobius_graph",
  "min_episodes": 5,
  "transition_stability_threshold": 0.6
}
```

Response:
```json
{
  "promoted": 1,
  "skipped": 3,
  "nodes": [
    {
      "bp_id": "BP-mobius_graph-9fa06eed",
      "pattern_signature": "FAN_OUT->TRIANGLE->CHAIN",
      "episode_count": 6,
      "transition_probabilities": {
        "FAN_OUT->TRIANGLE": 1.0,
        "TRIANGLE->CHAIN": 1.0
      },
      "first_seen": "2025-01-01T00:00:00",
      "last_seen": "2025-01-20T00:00:00",
      "graph_name": "mobius_graph"
    }
  ]
}
```

---

### Read-back endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/mobius/layer5/bevs/{graph_name}` | List all BEv nodes for a graph |
| GET | `/api/v1/mobius/layer5/bes/{graph_name}` | List all BE nodes for a graph |
| GET | `/api/v1/mobius/layer5/bps/{graph_name}` | List all BP nodes for a graph |

---

## 8. Test cases

Full test inputs and expected outputs are in [`test_cases.json`](test_cases.json).

### BEv test cases summary

| Test | Input | Expected | Tests |
|------|-------|----------|-------|
| TC-BEV-01 | 3 CONFIRMED FRAUD_SEQUENCE | 1 BEv promoted | Happy path |
| TC-BEV-02 | 1 CONFIRMED + 1 PENDING + 1 CANDIDATE | Only 1 promoted | PENDING/CANDIDATE exclusion |
| TC-BEV-03 | 3 different episode types | 3 BEv nodes | One BEv per archetype |
| TC-BEV-04 | 2 FRAUD + 1 WASH, threshold=3 | 0 promoted | Below threshold |
| TC-BEV-05 | 3 FRAUD, threshold=3 | 1 promoted | Exactly at threshold |
| TC-BEV-06 | No episodes | 0 promoted | Empty input |
| TC-BEV-07 | All 5 episode types | 5 BEv nodes | Full archetype coverage |

### BE test cases summary

| Test | Input | Expected | Tests |
|------|-------|----------|-------|
| TC-BE-01 | confidence=0.95, windows=5, parts=3, eps=4 | Promoted | Happy path |
| TC-BE-02 | confidence=0.75 | Skipped | Fails criterion 1 |
| TC-BE-03 | window_count=2 | Skipped | Fails criterion 2 |
| TC-BE-04 | partition_count=1 | Skipped | Fails criterion 3 |
| TC-BE-05 | episode_count=1 | Skipped | Fails criterion 4 |
| TC-BE-06 | All exactly at threshold | Promoted | Boundary condition |
| TC-BE-07 | 4 entities mixed | 2 promoted, 2 skipped | Real-world mix |

### BP test cases summary

| Test | Input | Expected | Tests |
|------|-------|----------|-------|
| TC-BP-01 | 6 episodes, 100% stable transitions | 1 BP promoted | Happy path |
| TC-BP-02 | 2 episodes only | Skipped | Too few episodes |
| TC-BP-03 | 50/50 transitions | Skipped | Unstable transitions |
| TC-BP-04 | Exactly 5 episodes at threshold | Promoted | Boundary condition |
| TC-BP-05 | 2 patterns — 1 stable, 1 rare | 1 promoted, 1 skipped | Mixed |
| TC-BP-06 | No sequences | 0 promoted | Empty input |

---

## 9. Mock seed data

Since Layer 4 (A1-A4) is not yet built, `seed_mock.py` inserts the exact data those tasks would produce. This lets us build and test Layer 5 in isolation.

**What gets seeded (`graph_name: mobius_graph`):**

| Type | Count | Purpose |
|------|-------|---------|
| Episode nodes | 10 | Mix of CONFIRMED (9) and PENDING (1) across 4 episode types |
| ResolvedEntity nodes | 5 | Mix of promotable (3) and non-promotable (2) |
| MotifSequence nodes | 5 | Mix of stable patterns (4) and rare patterns (1) |

**Run seeder:**
```bash
venv/bin/python seed_mock.py
```

**When real pipeline is ready:** Replace `seed_mock.py` with actual Layer 4 Neo4j reads. No changes needed to the extractors — they already read from Neo4j.

---

## 10. Dependency chain

```
A1 (Varada)  — Layer 4 schema
A2 (Varada)  — Episode assembler → produces MotifSequence nodes  →  needed by BP (B4)
A3 (Varada)  — Confidence scoring → produces CONFIRMED episodes  →  needed by BEv (B2)
A4 (Sindhura)— Identity resolution → produces ResolvedEntity nodes → needed by BE (B3)
B1           — Layer 5 schema (this service, schema.py)
B2 (Kiran)   — BEv extraction  ← needs A3 + B1   →  AG-528
B3 (Kiran)   — BE extraction   ← needs A4 + B1   →  AG-529
B4 (Kiran)   — BP extraction   ← needs A2 + B1 + B2 → AG-530
B5 (Ravindra)— Promotion engine ← needs B2 + B3 + B4
```

**Current approach:** A1-A4 mocked via `seed_mock.py`. Extractors work independently of the real A-group pipeline.

---

## 11. Archetype mapping table

| Episode Type | BEv Archetype | Meaning |
|-------------|---------------|---------|
| `FRAUD_SEQUENCE` | `FRAUDULENT_COORDINATION` | Multiple actors coordinating fraud |
| `COORDINATED_RATING` | `SYNTHETIC_RATING_EVENT` | Fake ratings being manufactured |
| `WASH_TRADING` | `WASH_TRADE_EVENT` | Circular value transfers to fake volume |
| `DATA_EXFILTRATION` | `OPERATIONAL_SECURITY_EVENT` | Unauthorized data leaving the system |
| `SENSOR_FAILURE_PATTERN` | `CASCADING_INFRASTRUCTURE_FAILURE` | Chain of sensor/infrastructure failures |
| `UNKNOWN` | `ANOMALOUS_EVENT` | Fallback for unrecognized episode types |
