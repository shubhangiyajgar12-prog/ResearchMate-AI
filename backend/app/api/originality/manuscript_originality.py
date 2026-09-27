from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.research_project import ResearchProject
from app.models.manuscript import Manuscript
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.services.originality.text_chunker import create_chunks
from app.services.originality.similarity_engine import find_similar_chunks
from app.services.originality.citation_service import (
    clean_research_text,
    split_sentences,
    looks_like_claim,
    classify_claim,
    has_citation,
    recommend_sources_for_claim,
)

router = APIRouter(prefix="/originality", tags=["Originality & Citations"])


class ManuscriptOriginalityRequest(BaseModel):
    project_id: int = Field(..., ge=1)


def _project_or_404(project_id: int, db: Session) -> ResearchProject:
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")
    return project


def _manuscript_or_404(project_id: int, db: Session) -> Manuscript:
    manuscript = (
        db.query(Manuscript)
        .filter(Manuscript.project_id == project_id)
        .order_by(Manuscript.updated_at.desc(), Manuscript.id.desc())
        .first()
    )
    if not manuscript:
        raise HTTPException(
            status_code=404,
            detail="No manuscript exists for this research project. Open Research Writing first.",
        )
    return manuscript


def _manuscript_text(manuscript: Manuscript) -> str:
    parts: list[str] = []
    if manuscript.title:
        parts.append(str(manuscript.title))
    if manuscript.abstract:
        parts.append(str(manuscript.abstract))
    sections = manuscript.sections if isinstance(manuscript.sections, dict) else {}
    for key, value in sections.items():
        if isinstance(value, str) and value.strip():
            parts.append(value)
    text = "\n\n".join(parts).strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="The project manuscript is empty. Add manuscript content in Research Writing first.",
        )
    return text


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", text.lower())
        if token not in {
            "the", "and", "for", "with", "from", "that", "this", "using",
            "based", "method", "system", "research", "study", "paper", "data",
            "analysis", "approach", "model", "proposed", "results", "section",
        }
    }


def _relevance_score(project: ResearchProject, paper: LiteraturePaper) -> float:
    project_text = " ".join(
        str(x or "")
        for x in (project.title, project.description, project.research_field)
    )
    paper_text = " ".join(
        str(x or "")
        for x in (paper.title, paper.abstract)
    )
    p = _tokens(project_text)
    s = _tokens(paper_text)
    if not p or not s:
        return 0.0
    return len(p & s) / max(1, min(len(p), len(s)))


def _evidence_sources(project_id: int, db: Session, manuscript: Manuscript) -> tuple[list[dict], int, int]:
    papers = (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == project_id)
        .order_by(LiteraturePaper.id.asc())
        .all()
    )

    evidence: list[dict] = []
    analyzed_count = 0
    usable_count = 0

    for paper in papers:
        # A manuscript may have a legacy paper_id. It is never treated as
        # the manuscript target, and is excluded from evidence if it is the
        # same source to avoid self-comparison.
        if manuscript.paper_id and paper.id == manuscript.paper_id:
            continue

        analysis = (
            db.query(PaperAnalysis)
            .filter(
                PaperAnalysis.literature_paper_id == paper.id,
                PaperAnalysis.project_id == project_id,
            )
            .order_by(PaperAnalysis.id.desc())
            .first()
        )
        if not analysis:
            continue
        analyzed_count += 1

        text = analysis.extracted_text or ""
        if not text.strip():
            continue
        usable_count += 1

        score = _relevance_score(project=db.query(ResearchProject).filter(ResearchProject.id == project_id).first(), paper=paper)
        # Clearly irrelevant papers are excluded from originality evidence.
        # A low score is still retained when the project has very little
        # metadata, but never crosses project boundaries.
        if score < 0.015:
            continue

        evidence.append({
            "paper": paper,
            "analysis": analysis,
            "relevance_score": round(score, 4),
        })

    return evidence, analyzed_count, usable_count


def _similarity_for_manuscript(project_id: int, manuscript: Manuscript, db: Session) -> dict[str, Any]:
    raw_target = _manuscript_text(manuscript)
    cleaned_target = clean_research_text(raw_target)
    if not cleaned_target.strip():
        raise HTTPException(status_code=400, detail="No usable manuscript text remains after cleaning.")

    target_chunks = create_chunks(cleaned_target, min_words=20, max_words=120)
    if not target_chunks:
        raise HTTPException(status_code=400, detail="Unable to create manuscript text chunks.")

    evidence, analyzed_count, usable_count = _evidence_sources(project_id, db, manuscript)
    all_matches: list[dict] = []
    compared_sources = 0

    for item in evidence:
        source_text = clean_research_text(item["analysis"].extracted_text or "")
        source_chunks = create_chunks(source_text, min_words=20, max_words=120)
        if not source_chunks:
            continue
        compared_sources += 1
        matches = find_similar_chunks(target_chunks, source_chunks, similarity_threshold=35.0)
        for match in matches:
            match = dict(match)
            match["source_paper_id"] = item["paper"].id
            match["source_title"] = item["paper"].title
            match["source_doi"] = item["paper"].doi
            match["source_url"] = item["paper"].url
            match["relevance_score"] = item["relevance_score"]
            all_matches.append(match)

    all_matches.sort(key=lambda x: float(x.get("similarity_score", 0)), reverse=True)

    # Overall overlap is deliberately defined as the percentage of manuscript
    # words contained in meaningful matched chunks. It is NOT "100 - score".
    matched_word_ids: set[int] = set()
    target_chunk_by_id = {int(c["chunk_id"]): c for c in target_chunks}
    for match in all_matches:
        cid = int(match["paper_chunk_id"])
        chunk = target_chunk_by_id.get(cid)
        if not chunk:
            continue
        # A chunk is counted once even if multiple sources match it.
        matched_word_ids.add(cid)

    total_target_words = len(re.findall(r"\b\w+\b", cleaned_target))
    matched_words = sum(
        len(re.findall(r"\b\w+\b", target_chunk_by_id[cid]["text"]))
        for cid in matched_word_ids
        if cid in target_chunk_by_id
    )
    overall = round((matched_words / total_target_words) * 100, 2) if total_target_words else 0.0

    return {
        "status": "completed",
        "project_id": project_id,
        "manuscript_id": manuscript.id,
        "target_type": "research_manuscript",
        "target_title": manuscript.title or "Untitled manuscript",
        "target_word_count": total_target_words,
        "target_chunks": len(target_chunks),
        "analyzed_project_papers": analyzed_count,
        "usable_full_text_sources": usable_count,
        "sources_checked": compared_sources,
        "overall_similarity": overall,
        "total_matches": len(all_matches),
        "matches": all_matches[:100],
        "method": "TF-IDF cosine similarity + exact word-overlap thresholding",
        "limitations": [
            "Similarity is a textual evidence signal, not a plagiarism verdict.",
            "Only same-project papers with extracted full text and non-trivial project relevance are compared.",
            "Metadata-only papers are not used for textual similarity.",
            "Semantic embedding similarity is not used by this endpoint.",
        ],
    }


def _citation_for_manuscript(project_id: int, manuscript: Manuscript, db: Session) -> dict[str, Any]:
    raw_text = _manuscript_text(manuscript)
    text = clean_research_text(raw_text)
    sentences = split_sentences(text)

    findings: list[dict] = []
    total_claims = 0
    citation_present_count = 0
    required_count = 0
    cited_required_count = 0
    by_type: dict[str, int] = {}

    for sentence in sentences:
        if not looks_like_claim(sentence):
            continue
        classification = classify_claim(sentence)
        total_claims += 1
        claim_type = classification.get("claim_type") or classification.get("type") or "General Statement"
        by_type[claim_type] = by_type.get(claim_type, 0) + 1
        present = bool(has_citation(sentence))
        if present:
            citation_present_count += 1

        needed = bool(classification.get("citation_needed"))
        if needed:
            required_count += 1
            if present:
                cited_required_count += 1

        recommendations = []
        if needed:
            try:
                recommendations = recommend_sources_for_claim(
                    db=db,
                    claim=sentence,
                    project_id=project_id,
                    target_paper_id=manuscript.paper_id,
                    limit=3,
                ) or []
            except Exception:
                recommendations = []

        findings.append({
            "claim_text": sentence,
            "claim_type": claim_type,
            "citation_present": "yes" if present else "no",
            "citation_needed": "yes" if needed else "no",
            "confidence": float(classification.get("confidence") or 0.0),
            "suggested_sources": recommendations,
            "explanation": classification.get("reason") or classification.get("explanation"),
        })

    coverage = round((cited_required_count / required_count) * 100, 2) if required_count else 100.0
    missing = sum(1 for f in findings if f["citation_needed"] == "yes" and f["citation_present"] == "no")

    return {
        "status": "completed",
        "project_id": project_id,
        "manuscript_id": manuscript.id,
        "target_type": "research_manuscript",
        "total_claims": total_claims,
        "citations_present": citation_present_count,
        "citation_required_claims": required_count,
        "cited_required_claims": cited_required_count,
        "potential_missing_citations": missing,
        "citation_coverage": coverage,
        "claim_types": by_type,
        "findings": findings[:150],
        "limitations": [
            "Citation need is an evidence-based heuristic; review borderline claims manually.",
            "Own methodology and own results are not automatically treated as requiring external citations.",
            "Suggested sources come only from the active project's stored literature.",
        ],
    }


@router.post("/projects/{project_id}/manuscript-similarity")
def manuscript_similarity(
    project_id: int,
    request: ManuscriptOriginalityRequest,
    db: Session = Depends(get_db),
):
    if request.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id in body does not match URL.")
    _project_or_404(project_id, db)
    manuscript = _manuscript_or_404(project_id, db)
    return _similarity_for_manuscript(project_id, manuscript, db)


@router.post("/projects/{project_id}/manuscript-citation-analysis")
def manuscript_citation_analysis(
    project_id: int,
    request: ManuscriptOriginalityRequest,
    db: Session = Depends(get_db),
):
    if request.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id in body does not match URL.")
    _project_or_404(project_id, db)
    manuscript = _manuscript_or_404(project_id, db)
    return _citation_for_manuscript(project_id, manuscript, db)


@router.post("/projects/{project_id}/manuscript-full-check")
def manuscript_full_check(
    project_id: int,
    request: ManuscriptOriginalityRequest,
    db: Session = Depends(get_db),
):
    if request.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id in body does not match URL.")
    _project_or_404(project_id, db)
    manuscript = _manuscript_or_404(project_id, db)
    similarity = _similarity_for_manuscript(project_id, manuscript, db)
    citation = _citation_for_manuscript(project_id, manuscript, db)
    return {
        "status": "completed",
        "project_id": project_id,
        "manuscript_id": manuscript.id,
        "target_type": "research_manuscript",
        "manuscript": {
            "title": manuscript.title or "Untitled manuscript",
            "word_count": similarity["target_word_count"],
        },
        "similarity": similarity,
        "citation": citation,
        "evidence_sources": [
            {
                "source_paper_id": m["source_paper_id"],
                "source_title": m["source_title"],
                "source_doi": m.get("source_doi"),
                "source_url": m.get("source_url"),
                "relevance_score": m.get("relevance_score"),
            }
            for m in similarity["matches"]
        ],
        "limitations": [
            "This report provides textual similarity and citation-review evidence; it does not certify originality, novelty, or absence of plagiarism.",
        ],
    }
