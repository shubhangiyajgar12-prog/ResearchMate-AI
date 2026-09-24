"""Evidence-first cross-paper research-gap endpoint.

The endpoint only promotes explicit limitation/challenge evidence into a
potential follow-up signal. It does not claim novelty or a definitive gap
when the saved abstracts do not support one.
"""
import re
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper

router = APIRouter(prefix="/literature", tags=["Literature Intelligence"])


class ResearchGapRequest(BaseModel):
    paper_ids: list[int] = Field(min_length=2)


def clean(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def sentences(text):
    return [x.strip(" -") for x in re.split(r"(?<=[.!?])\s+", clean(text)) if len(x.strip(" -")) >= 25]


def limitation_evidence(text):
    patterns = [
        r"\blimitations?\b",
        r"\blimited\b",
        r"\black of\b",
        r"\bsmall sample\b",
        r"\bsmall dataset\b",
        r"\bchallenge(?:s|d)?\b",
        r"\bfuture work\b",
        r"\bneeds? further (?:research|investigation|study)\b",
        r"\bremains? unclear\b",
    ]
    return [
        s for s in sentences(text)
        if any(re.search(pattern, s, re.I) for pattern in patterns)
    ][:2]


def limitation_category(evidence):
    low = " ".join(evidence).lower()
    if re.search(r"dataset|sample|participants|cases|records", low):
        return "Data or sample limitation"
    if re.search(r"future work|further research|further investigation|remains unclear", low):
        return "Unresolved area identified by the authors"
    if re.search(r"challenge", low):
        return "Method or implementation challenge"
    if re.search(r"lack of|limited|limitation", low):
        return "Explicit limitation reported by the authors"
    return "Explicit limitation/challenge"


@router.post("/research-gap")
def research_gap(project_id: int, request: ResearchGapRequest, db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(request.paper_ids))
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least two saved papers for cross-paper research-gap analysis.")

    papers = (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == project_id, LiteraturePaper.id.in_(ids))
        .order_by(LiteraturePaper.id.asc())
        .all()
    )
    found = {p.id for p in papers}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"One or more selected papers were not found in project: {missing}")

    evidence_rows = []
    category_counter = Counter()
    for paper in papers:
        evidence = limitation_evidence(paper.abstract)
        if evidence:
            category = limitation_category(evidence)
            category_counter[category] += 1
            evidence_rows.append({
                "paper_id": paper.id,
                "title": clean(paper.title) or "Untitled paper",
                "category": category,
                "evidence": evidence,
            })

    patterns = []
    years = [p.year for p in papers if p.year]
    if years:
        patterns.append({
            "type": "publication_span",
            "label": "Publication span",
            "evidence": f"Selected papers span publication years {min(years)}–{max(years)}.",
            "basis": "Saved publication-year metadata",
        })
    if evidence_rows:
        patterns.append({
            "type": "explicit_limitation_signals",
            "label": "Explicit limitation signals",
            "evidence": [
                {
                    "title": row["title"],
                    "category": row["category"],
                }
                for row in evidence_rows
            ],
            "basis": "Sentences in saved abstracts containing explicit limitation/challenge language",
        })

    # A cross-paper gap is only emitted when the same limitation category is
    # explicitly present in at least two selected papers.
    gaps = []
    repeated_categories = {cat for cat, count in category_counter.items() if count >= 2}
    for category in sorted(repeated_categories):
        affected = [row for row in evidence_rows if row["category"] == category]
        gaps.append({
            "gap": f"Repeated {category.lower()} across selected papers",
            "evidence": [
                {
                    "title": row["title"],
                    "statement": statement,
                }
                for row in affected
                for statement in row["evidence"]
            ],
            "affected_papers": [
                {"id": row["paper_id"], "title": row["title"]}
                for row in affected
            ],
            "evidence_strength": "Explicit in multiple abstracts",
            "research_opportunity": "Investigate this repeated limitation with a clearly defined method, dataset, or evaluation setting, then verify the original papers and broader recent literature before calling it a research gap.",
        })

    # Single-paper limitations are useful evidence, but are not presented as
    # cross-paper research gaps.
    opportunities = []
    for row in evidence_rows:
        opportunities.append({
            "title": row["title"],
            "category": row["category"],
            "evidence": row["evidence"],
            "paper_id": row["paper_id"],
        })

    if gaps:
        summary = "The selected abstracts contain repeated explicit limitation signals. These are potential research-gap signals, not proof of novelty; full-text and broader recent-literature verification is required."
    elif evidence_rows:
        summary = "The selected abstracts contain explicit limitation signals, but they are not repeated across multiple selected papers. A cross-paper research gap is therefore not established from these records alone."
    else:
        summary = "No explicit limitation or research-gap statement was found in the selected saved abstracts. A defensible cross-paper research-gap claim requires full-text evidence and a broader recent-literature review."

    return {
        "project_id": project_id,
        "paper_ids": ids,
        "gaps": gaps,
        "research_gaps": gaps,
        "cross_paper_patterns": patterns,
        "cross_paper_findings": patterns,
        "follow_up_opportunities": opportunities,
        "overall_summary": summary,
        "research_gap_summary": summary,
        "gap_count": len(gaps),
        "evidence_note": "Evidence-first deterministic synthesis from saved paper titles/abstracts. No definitive novelty or research-gap claim is made without explicit cross-paper evidence.",
    }
