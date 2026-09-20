from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.literature_paper import (
    LiteraturePaper,
)

from app.models.paper_analysis import (
    PaperAnalysis,
)

from app.schemas.literature.research_gap import (
    ResearchGapRequest,
    ResearchGapResponse,
)

from app.services.literature.research_gap import (
    generate_research_gap,
)


router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"],
)


# ============================================================
# RESEARCH GAP
# ============================================================

@router.post(
    "/research-gap",
    response_model=ResearchGapResponse,
)
def research_gap(
    request: ResearchGapRequest,
    project_id: int = Query(...),
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Validate project ID
    # --------------------------------------------------------

    if project_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="project_id must be a positive integer.",
        )

    # --------------------------------------------------------
    # Validate paper IDs
    # --------------------------------------------------------

    if not request.paper_ids:

        raise HTTPException(
            status_code=400,
            detail="At least one paper ID is required.",
        )

    # Remove duplicate IDs
    paper_ids = list(
        dict.fromkeys(
            request.paper_ids
        )
    )

    # --------------------------------------------------------
    # Fetch selected papers
    # --------------------------------------------------------

    papers = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id,
            LiteraturePaper.id.in_(paper_ids),
        )
        .all()
    )

    # --------------------------------------------------------
    # No papers found
    # --------------------------------------------------------

    if not papers:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No selected papers found "
                f"in project {project_id}."
            ),
        )

    # --------------------------------------------------------
    # Check missing IDs
    # --------------------------------------------------------

    found_ids = {
        paper.id
        for paper in papers
    }

    missing_ids = [
        paper_id
        for paper_id in paper_ids
        if paper_id not in found_ids
    ]

    if missing_ids:

        raise HTTPException(
            status_code=404,
            detail={
                "message": (
                    "Some selected papers were "
                    "not found in this project."
                ),
                "missing_paper_ids": missing_ids,
                "project_id": project_id,
            },
        )

    # --------------------------------------------------------
    # Preserve user-selected order
    # --------------------------------------------------------

    paper_map = {
        paper.id: paper
        for paper in papers
    }

    ordered_papers = [
        paper_map[paper_id]
        for paper_id in paper_ids
    ]

    # --------------------------------------------------------
    # Prepare AI context
    # --------------------------------------------------------

    paper_data = []

    for paper in ordered_papers:

        # IMPORTANT:
        #
        # PaperAnalysis has:
        #
        # literature_paper_id
        #
        # NOT paper_id
        #

        analysis = (
            db.query(PaperAnalysis)
            .filter(
                PaperAnalysis.literature_paper_id
                == paper.id,

                PaperAnalysis.project_id
                == project_id,
            )
            .first()
        )

        analysis_json = {}

        if (
            analysis
            and analysis.analysis_json
        ):
            analysis_json = (
                analysis.analysis_json
            )

        # ----------------------------------------------------
        # Authors
        # ----------------------------------------------------

        authors = []

        if paper.authors:

            authors = [
                author.strip()
                for author
                in paper.authors.split(",")
                if author.strip()
            ]

        # ----------------------------------------------------
        # Build paper object
        # ----------------------------------------------------

        paper_data.append(
            {
                "paper_id": paper.id,

                "title": (
                    paper.title
                    or "Untitled paper"
                ),

                "year": paper.year,

                "authors": authors,

                "abstract": (
                    paper.abstract
                    or ""
                ),

                "analysis": analysis_json,

                "has_pdf_analysis": (
                    analysis is not None
                ),
            }
        )

    # --------------------------------------------------------
    # Generate AI research gap
    # --------------------------------------------------------

    try:

        result = generate_research_gap(
            project_id=project_id,
            papers=paper_data,
        )

        return result

    except Exception as error:

        print("\n")
        print("=" * 70)
        print("RESEARCH GAP AI ERROR")
        print("=" * 70)
        print(
            type(error).__name__
        )
        print(str(error))
        print("=" * 70)
        print("\n")

        raise HTTPException(
            status_code=500,
            detail=(
                "Research gap generation failed: "
                f"{str(error)}"
            ),
        )