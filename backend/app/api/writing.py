from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.schemas.writing import WritingAnalysisRequest
from app.services.writing.writing_service import WritingService


router = APIRouter(
    prefix="/writing",
    tags=["Writing"]
)


@router.post(
    "/projects/{project_id}/papers/{paper_id}/analyze"
)
def analyze_writing(
    project_id: int,
    paper_id: int,
    request: WritingAnalysisRequest,
    db: Session = Depends(get_db)
):

    # ---------------------------------------------------------
    # 1. Check paper
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
        .order_by(PaperAnalysis.id.desc())
        .first()
    )

    # ---------------------------------------------------------
    # 3. Manuscript source
    # ---------------------------------------------------------

    manuscript = request.manuscript.strip()

    if not manuscript and analysis:
        manuscript = analysis.extracted_text or ""

    if not manuscript:
        raise HTTPException(
            status_code=400,
            detail="No manuscript text available for analysis."
        )

    # ---------------------------------------------------------
    # 4. Title
    # ---------------------------------------------------------

    title = request.title.strip()

    if not title:
        title = paper.title or ""

    # ---------------------------------------------------------
    # 5. Abstract
    # ---------------------------------------------------------

    abstract = request.abstract.strip()

    # ---------------------------------------------------------
    # 6. Limit extremely large input
    # ---------------------------------------------------------

    max_chars = 60000

    if len(manuscript) > max_chars:
        manuscript = manuscript[:max_chars]

    # ---------------------------------------------------------
    # 7. Gemini Writing Analysis
    # ---------------------------------------------------------

    try:

        service = WritingService()

        result = service.analyze_paper(
            title=title,
            abstract=abstract,
            manuscript=manuscript
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Writing analysis failed: {str(e)}"
        )

    # ---------------------------------------------------------
    # 8. Return complete result
    # ---------------------------------------------------------

    return {
        "project_id": project_id,
        "paper_id": paper_id,

        "paper_title": title,

        "paper_structure": result.get(
            "paper_structure",
            {}
        ),

        "title_suggestions": result.get(
            "title_suggestions",
            []
        ),

        "abstract_feedback": result.get(
            "abstract_feedback",
            {}
        ),

        "academic_writing_feedback": result.get(
            "academic_writing_feedback",
            {}
        ),

        "citation_reference_feedback": result.get(
            "citation_reference_feedback",
            {}
        ),

        "formatting_feedback": result.get(
            "formatting_feedback",
            {}
        ),

        "overall_recommendations": result.get(
            "overall_recommendations",
            []
        ),

        "strengths": result.get(
            "strengths",
            []
        ),

        "improvement_areas": result.get(
            "improvement_areas",
            []
        )
    }