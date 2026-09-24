from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.schemas.reviewer import ReviewerRequest

from app.services.reviewer.reviewer_service import (
    ReviewerService
)


router = APIRouter(
    prefix="/reviewer",
    tags=["AI Reviewer"]
)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/review"
)
def review_paper(
    project_id: int,
    paper_id: int,
    request: ReviewerRequest,
    db: Session = Depends(get_db)
):

    # ---------------------------------------------------------
    # 1. Verify paper belongs to project
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
    # 2. Get latest paper analysis
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

    # ---------------------------------------------------------
    # 3. Manuscript source
    # ---------------------------------------------------------

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
    # 4. Limit context
    # ---------------------------------------------------------

    max_chars = 60000

    if len(manuscript) > max_chars:

        manuscript = manuscript[:max_chars]

    # ---------------------------------------------------------
    # 5. AI Reviewer
    # ---------------------------------------------------------

    try:

        service = ReviewerService()

        result = service.review_paper(
            manuscript=manuscript
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"AI reviewer failed: {str(e)}"
        )

    # ---------------------------------------------------------
    # 6. Response
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "paper_id": paper_id,
        "paper_title": paper.title,

        "overall_review": result.get(
            "overall_review",
            ""
        ),

        "novelty_review": result.get(
            "novelty_review",
            {}
        ),

        "methodology_review": result.get(
            "methodology_review",
            {}
        ),

        "dataset_review": result.get(
            "dataset_review",
            {}
        ),

        "experiment_review": result.get(
            "experiment_review",
            {}
        ),

        "results_review": result.get(
            "results_review",
            {}
        ),

        "discussion_review": result.get(
            "discussion_review",
            {}
        ),

        "citation_review": result.get(
            "citation_review",
            {}
        ),

        "major_concerns": result.get(
            "major_concerns",
            []
        ),

        "minor_concerns": result.get(
            "minor_concerns",
            []
        ),

        "technical_issues": result.get(
            "technical_issues",
            []
        ),

        "reviewer_questions": result.get(
            "reviewer_questions",
            []
        ),

        "strengths": result.get(
            "strengths",
            []
        ),

        "improvement_priorities": result.get(
            "improvement_priorities",
            []
        ),

        "reviewer_recommendation": result.get(
            "reviewer_recommendation",
            ""
        )
    }