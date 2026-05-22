from fastapi import FastAPI
from models import ExtractBEvRequest, ExtractBERequest, ExtractBPRequest, ExtractBLRequest, ExtractionResult
from extractor_bev import extract_bevs
from extractor_be import extract_bes
from extractor_bp import extract_bps
from extractor_bl import extract_bls
from validator_compression import validate_compression
from schema import init_schema
from seed_mock import seed
from db import get_session

app = FastAPI(title="BPAC Extraction Service", version="1.0.0")


@app.on_event("startup")
def on_startup():
    init_schema()


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.post("/admin/init-schema")
def admin_init_schema():
    return init_schema()


@app.post("/admin/seed-mock")
def admin_seed(graph_name: str = "mobius_graph"):
    return seed(graph_name)


# ── B2 — Business Event (BEv) ─────────────────────────────────────────────────

@app.post("/api/v1/mobius/layer5/extract/events", response_model=ExtractionResult)
def extract_events(req: ExtractBEvRequest):
    return extract_bevs(req)


# ── B3 — Business Entity (BE) ─────────────────────────────────────────────────

@app.post("/api/v1/mobius/layer5/extract/entities", response_model=ExtractionResult)
def extract_entities(req: ExtractBERequest):
    return extract_bes(req)


# ── B4 — Business Process (BP) ────────────────────────────────────────────────

@app.post("/api/v1/mobius/layer5/extract/processes", response_model=ExtractionResult)
def extract_processes(req: ExtractBPRequest):
    return extract_bps(req)


# ── AG-538 — Business Law (BL) ────────────────────────────────────────────────

@app.post("/api/v1/mobius/layer5/extract/laws", response_model=ExtractionResult)
def extract_laws(req: ExtractBLRequest):
    return extract_bls(req)


# ── AG-539 — Compression rule validator ───────────────────────────────────────

@app.get("/api/v1/mobius/layer5/validate/compression/{graph_name}")
def compression_check(graph_name: str):
    return validate_compression(graph_name)


# ── AG-540 — Review queue ─────────────────────────────────────────────────────

@app.get("/api/v1/mobius/layer5/review-queue/{graph_name}")
def get_review_queue(graph_name: str):
    with get_session() as session:
        result = session.run(
            "MATCH (q:ReviewQueueItem {graph_name: $g}) RETURN q",
            g=graph_name
        )
        return [dict(r["q"]) for r in result]


# ── Read-back ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/mobius/layer5/bevs/{graph_name}")
def list_bevs(graph_name: str):
    with get_session() as session:
        result = session.run("MATCH (b:BEv {graph_name: $g}) RETURN b", g=graph_name)
        return [dict(r["b"]) for r in result]


@app.get("/api/v1/mobius/layer5/bes/{graph_name}")
def list_bes(graph_name: str):
    with get_session() as session:
        result = session.run("MATCH (b:BE {graph_name: $g}) RETURN b", g=graph_name)
        return [dict(r["b"]) for r in result]


@app.get("/api/v1/mobius/layer5/bps/{graph_name}")
def list_bps(graph_name: str):
    with get_session() as session:
        result = session.run("MATCH (b:BP {graph_name: $g}) RETURN b", g=graph_name)
        return [dict(r["b"]) for r in result]


@app.get("/api/v1/mobius/layer5/bls/{graph_name}")
def list_bls(graph_name: str):
    with get_session() as session:
        result = session.run("MATCH (b:BL {graph_name: $g}) RETURN b", g=graph_name)
        return [dict(r["b"]) for r in result]
