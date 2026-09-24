from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.schemas.publication import PublicationRequest

from app.services.publication.publication_service import (
    PublicationService
)


router = APIRouter(
    prefix="/publication",
    tags=["Publication Assistant"]
)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/analyze"
)
def analyze_publication(
    project_id: int,
    paper_id: int,
    request: PublicationRequest,
    db: Session = Depends(get_db)
):

    # ---------------------------------------------------------
    # 1. Verify paper
    # ---------------------------------------------------------

    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id
        )
        .first()
    )

    if not paper:

        raise HTTPException(
            status_code=404,
            detail="Paper not found in this project."
        )

    # ---------------------------------------------------------
    # 2. Latest extracted paper text
    # ---------------------------------------------------------

    analysis = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.literature_paper_id == paper_id
        )
        .order_by(
            PaperAnalysis.id.desc()
        )
        .first()
    )

    manuscript = request.manuscript.strip()

    if not manuscript and analysis:

        manuscript = (
            analysis.extracted_text
            or ""
        )

    if not manuscript:

        raise HTTPException(
            status_code=400,
            detail="No manuscript text available."
        )

    # ---------------------------------------------------------
    # 3. Research field
    # ---------------------------------------------------------

    research_field = request.research_field.strip()

    if not research_field:

        research_field = "Computer Science / Artificial Intelligence"

    # ---------------------------------------------------------
    # 4. Limit context
    # ---------------------------------------------------------

    max_chars = 60000

    if len(manuscript) > max_chars:
        manuscript = manuscript[:max_chars]

    # ---------------------------------------------------------
    # 5. Publication analysis
    # ---------------------------------------------------------

    try:

        service = PublicationService()

        result = service.analyze_publication(
            manuscript=manuscript,
            research_field=research_field
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Publication analysis failed: {str(e)}"
        )

    # ---------------------------------------------------------
    # 6. Response
    # ---------------------------------------------------------

    journals = result.get("journal_recommendations", [])
    conferences = result.get("conference_recommendations", [])
    checklist = result.get("submission_checklist", [])
    complete = sum(1 for x in checklist if str(x.get("status", "")).lower() in {"complete", "ready", "present"})
    readiness = round((complete / len(checklist)) * 100) if checklist else None
    venues = []
    for v in journals + conferences:
        venues.append({
            "name": v.get("name", "Potential venue"),
            "type": "Journal" if v in journals else "Conference",
            "publisher": v.get("publisher", ""),
            "scope": v.get("research_scope", ""),
            "fit": v.get("fit_reason", "Potential fit"),
            "open_access": v.get("open_access", ""),
            "requirements": v.get("requirements", []),
            "url": v.get("official_url"),
            "verification_required": v.get("verification_required", True),
        })
    return {
        "project_id": project_id, "paper_id": paper_id, "paper_title": paper.title,
        "field": research_field, "readiness_score": readiness,
        "venues": venues, "checklist": checklist,
        "missing_items": result.get("missing_submission_items", []),
        "requirements": result.get("manuscript_requirements", []),
        "deadlines": result.get("cfp_and_deadline_notes", []),
        "risks": result.get("predatory_risk_checks", []),
        "plan": result.get("preparation_plan", []),
        "notes": result.get("important_warnings", []),
        "publication_strategy": result.get("publication_strategy", ""),
        "publication_fit": result.get("publication_fit", {}),
        "journal_recommendations": journals,
        "conference_recommendations": conferences,
    }