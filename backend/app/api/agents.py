from fastapi import APIRouter
from app.services.agents.orchestrator import orchestrator
from app.services.rag.rag_service import rag_service

router = APIRouter(prefix="/ai", tags=["RAG & Agents"])

@router.post("/rag/index")
def index_document(payload: dict):
    chunks = rag_service.index_document(payload.get("text", ""), payload.get("metadata") or {})
    return {"success": True, "chunks_indexed": len(chunks), "chunks": chunks[:3]}

@router.post("/rag/search")
def search_rag(payload: dict):
    return {"success": True, "results": rag_service.search(payload.get("query", ""), int(payload.get("top_k", 5)))}

@router.post("/agents/analyze")
def run_agents(payload: dict):
    return orchestrator.run(payload.get("manuscript", ""), payload.get("research_field", "Computer Science"), payload.get("query"))
