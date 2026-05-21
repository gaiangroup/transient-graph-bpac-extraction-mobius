from fastapi import FastAPI, HTTPException
from models import ExtractBEvRequest, ExtractBERequest, ExtractBPRequest, ExtractionResult
from extractor_bev import extract_bevs
from extractor_be import extract_bes
from extractor_bp import extract_bps
from schema import init_schema
from seed_mock import seed

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


# ── B4 — Business Process (BP) ───────────────────────────────────────────────

@app.post("/api/v1/mobius/layer5/extract/processes", response_model=ExtractionResult)
def extract_processes(req: ExtractBPRequest):
    return extract_bps(req)


# ── Read-back ─────────────────────────────────────────────────────────────────

@app.get("/api/v1/mobius/layer5/bevs/{graph_name}")
def list_bevs(graph_name: str):
    from db import get_session
    with get_session() as session:
        result = session.run(
            "MATCH (b:BEv {graph_name: $g}) RETURN b", g=graph_name
        )
        return [dict(r["b"]) for r in result]


@app.get("/api/v1/mobius/layer5/bes/{graph_name}")
def list_bes(graph_name: str):
    from db import get_session
    with get_session() as session:
        result = session.run(
            "MATCH (b:BE {graph_name: $g}) RETURN b", g=graph_name
        )
        return [dict(r["b"]) for r in result]


@app.get("/api/v1/mobius/layer5/bps/{graph_name}")
def list_bps(graph_name: str):
    from db import get_session
    with get_session() as session:
        result = session.run(
            "MATCH (b:BP {graph_name: $g}) RETURN b", g=graph_name
        )
        return [dict(r["b"]) for r in result]
