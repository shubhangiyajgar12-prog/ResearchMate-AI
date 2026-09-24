from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.schemas.improvement import ImprovementRequest

from app.services.improvement.improvement_service import (
    ImprovementService
)


router = APIRouter(
    prefix="/improvement",
    tags=["Improvement Planner"]
)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/plan"
)
def create_improvement_plan(
    project_id: int,
    paper_id: int,
    request: ImprovementRequest,
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
    # 2. Get latest analysis
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
    # 3. Manuscript
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
    # 4. Context limit
    # ---------------------------------------------------------

    max_chars = 60000

    if len(manuscript) > max_chars:
        manuscript = manuscript[:max_chars]

    # ---------------------------------------------------------
    # 5. Generate plan
    # ---------------------------------------------------------

    try:

        service = ImprovementService()

        result = service.create_plan(
            manuscript=manuscript
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Improvement planning failed: {str(e)}"
        )

    # ---------------------------------------------------------
    # 6. Response
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "paper_id": paper_id,
        "paper_title": paper.title,

        "overall_plan": result.get(
            "overall_plan",
            ""
        ),

        "priority_actions": result.get(
            "priority_actions",
            []
        ),

        "section_improvements": result.get(
            "section_improvements",
            []
        ),

        "methodology_improvements": result.get(
            "methodology_improvements",
            []
        ),

        "experiment_improvements": result.get(
            "experiment_improvements",
            []
        ),

        "writing_improvements": result.get(
            "writing_improvements",
            []
        ),

        "citation_improvements": result.get(
            "citation_improvements",
            []
        ),

        "formatting_improvements": result.get(
            "formatting_improvements",
            []
        ),

        "quick_fixes": result.get(
            "quick_fixes",
            []
        ),

        "long_term_improvements": result.get(
            "long_term_improvements",
            []
        ),

        "revised_structure": result.get(
            "revised_structure",
            []
        ),

        "implementation_order": result.get(
            "implementation_order",
            []
        )
    }