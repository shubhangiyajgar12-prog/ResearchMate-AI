"""Presentation-friendly multi-agent orchestration layer.
Agents are explicit, auditable steps; LLM use is centralized and optional."""
from typing import Any
from app.services.rag.rag_service import rag_service

class Agent:
    name = "Base Agent"
    def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

class PaperAnalysisAgent(Agent):
    name = "Paper Analyzer"
    def run(self, context):
        text = context.get("manuscript", "")
        sections = ["abstract", "introduction", "methodology", "results", "discussion", "limitations", "conclusion", "references"]
        lower = text.lower()
        found = [s for s in sections if s in lower]
        return {"agent": self.name, "status": "completed", "sections_found": found, "coverage": round(len(found)/len(sections)*100) if sections else 0}

class CitationAgent(Agent):
    name = "Citation Agent"
    def run(self, context):
        text = context.get("manuscript", "")
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        candidates = [s for s in sentences if len(s.split()) >= 10 and any(k in s.lower() for k in ("study", "research", "previous", "according", "reported", "shows"))]
        return {"agent": self.name, "status": "completed", "candidate_claims": len(candidates), "citation_note": "Claims are candidates for review; own methods/results are not automatically flagged."}

class OriginalityAgent(Agent):
    name = "Originality Agent"
    def run(self, context):
        text = context.get("manuscript", "")
        chunks = rag_service.search(text[:1200], top_k=3)
        return {"agent": self.name, "status": "completed", "indexed_matches": len(chunks), "method": "lexical evidence retrieval"}

class PublicationAgent(Agent):
    name = "Publication Agent"
    def run(self, context):
        text = context.get("manuscript", "")
        checks = {"title": bool(text.strip()), "abstract": "abstract" in text.lower(), "references": "references" in text.lower(), "methodology": "method" in text.lower()}
        return {"agent": self.name, "status": "completed", "checks": checks}

class ConferenceAgent(Agent):
    name = "Conference Agent"
    def run(self, context):
        field = context.get("research_field", "Computer Science")
        return {"agent": self.name, "status": "completed", "research_field": field, "verification": "Conference dates are returned only when sourced/verified."}

class ResearchOrchestrator:
    def __init__(self):
        self.agents = [PaperAnalysisAgent(), CitationAgent(), OriginalityAgent(), PublicationAgent(), ConferenceAgent()]

    def run(self, manuscript: str, research_field: str = "Computer Science", query: str | None = None):
        context = {"manuscript": manuscript, "research_field": research_field, "query": query}
        results = []
        for agent in self.agents:
            try:
                results.append(agent.run(context))
            except Exception as exc:
                results.append({"agent": agent.name, "status": "failed", "error": str(exc)})
        return {"workflow": "research_analysis", "status": "completed", "agents": results}

orchestrator = ResearchOrchestrator()
