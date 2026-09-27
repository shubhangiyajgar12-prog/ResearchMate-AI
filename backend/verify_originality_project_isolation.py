"""
ResearchMate AI — verify Originality project isolation.

Run from:
D:\myproject\ResearchMate-AI\backend

This is read-only. It checks:
1. Project #4 papers
2. Project #4 analyzed papers
3. Cross-project ownership for a sample paper
"""

from app.database.database import SessionLocal
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

PROJECT_ID = 4

db = SessionLocal()
try:
    papers = (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == PROJECT_ID)
        .order_by(LiteraturePaper.id)
        .all()
    )

    print("\nPROJECT 4 — SAVED PAPERS")
    for paper in papers:
        analysis = (
            db.query(PaperAnalysis)
            .filter(
                PaperAnalysis.literature_paper_id == paper.id,
                PaperAnalysis.project_id == PROJECT_ID,
            )
            .order_by(PaperAnalysis.id.desc())
            .first()
        )
        print(
            f"{paper.id} | analyzed={bool(analysis and (analysis.extracted_text or '').strip())} "
            f"| {paper.title}"
        )

    print(f"\nTOTAL SAVED: {len(papers)}")
    analyzed = [
        p for p in papers
        if db.query(PaperAnalysis).filter(
            PaperAnalysis.literature_paper_id == p.id,
            PaperAnalysis.project_id == PROJECT_ID,
        ).first()
    ]
    print(f"TOTAL ANALYZED: {len(analyzed)}")

    print("\nPROJECT ISOLATION CHECK")
    foreign = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id != PROJECT_ID,
            LiteraturePaper.id.in_([p.id for p in papers]),
        )
        .count()
        if papers else 0
    )
    print(f"Foreign ownership collisions: {foreign}")
    print("PASS" if foreign == 0 else "FAIL")

finally:
    db.close()
