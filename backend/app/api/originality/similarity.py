from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.models.originality_reports import OriginalityReport
from app.models.similarity_match import SimilarityMatch

from app.schemas.originality.similarity import (
    OriginalityAnalysisRequest,
    OriginalityReportResponse,
    SimilarityMatchResponse,
)

from app.services.originality.originality_service import (
    analyze_project_paper,
)


router = APIRouter(
    prefix="/originality",
    tags=["Originality & Citations"],
)


# ============================================================
# ORIGINALITY / SIMILARITY ANALYSIS
# ============================================================

@router.post(
    "/projects/{project_id}/analyze",
    response_model=OriginalityReportResponse,
)
def analyze_originality(
    project_id: int,
    request: OriginalityAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Run textual similarity analysis for a research paper.

    Flow:

    Project
        ↓
    Target Paper
        ↓
    PDF Analysis / Extracted Text
        ↓
    Text Cleaning
        ↓
    Text Chunking
        ↓
    Similarity Engine
        ↓
    Originality Report
        ↓
    Similarity Matches
    """

    try:

        # ----------------------------------------------------
        # 1. Validate project_id
        # ----------------------------------------------------

        if request.project_id != project_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "project_id in request body does not match "
                    "project_id in URL."
                ),
            )

        # ----------------------------------------------------
        # 2. Validate target paper
        # ----------------------------------------------------

        target_paper = (
            db.query(LiteraturePaper)
            .filter(
                LiteraturePaper.id == request.paper_id,
                LiteraturePaper.project_id == project_id,
            )
            .first()
        )

        if not target_paper:
            raise HTTPException(
                status_code=404,
                detail="Target paper not found for this project.",
            )

        # ----------------------------------------------------
        # 3. Validate PDF analysis
        # ----------------------------------------------------

        paper_analysis = (
            db.query(PaperAnalysis)
            .filter(
                PaperAnalysis.literature_paper_id
                == request.paper_id,
                PaperAnalysis.project_id
                == project_id,
            )
            .order_by(PaperAnalysis.id.desc())
            .first()
        )

        if not paper_analysis:
            raise HTTPException(
                status_code=400,
                detail=(
                    "PDF analysis not found for this paper. "
                    "Please analyze the paper PDF first."
                ),
            )

        if not paper_analysis.extracted_text:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No extracted text found for this paper. "
                    "Please analyze the PDF again."
                ),
            )

        # ----------------------------------------------------
        # 4. Run originality analysis
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # The service expects:
        #
        #     paper_id
        #
        # NOT:
        #
        #     target_paper_id
        #
        # ----------------------------------------------------

        result = analyze_project_paper(
            db=db,
            project_id=project_id,
            paper_id=request.paper_id,
        )

        # ----------------------------------------------------
        # 5. Delete previous report for same paper
        # ----------------------------------------------------
        #
        # We delete the previous matches first because they
        # depend on the previous originality report.
        # ----------------------------------------------------

        old_reports = (
            db.query(OriginalityReport)
            .filter(
                OriginalityReport.project_id == project_id,
                OriginalityReport.paper_id == request.paper_id,
            )
            .all()
        )

        for old_report in old_reports:

            (
                db.query(SimilarityMatch)
                .filter(
                    SimilarityMatch.report_id
                    == old_report.id
                )
                .delete(
                    synchronize_session=False
                )
            )

            db.delete(old_report)

        db.flush()

        # ----------------------------------------------------
        # 6. Prepare report JSON
        # ----------------------------------------------------

        report_json = {
            "status": "completed",

            "project_id": project_id,

            "paper_id": request.paper_id,

            "target_title": result.get(
                "target_title"
            ),

            "target_chunks": result.get(
                "target_chunks",
                0,
            ),

            "sources_checked": result.get(
                "sources_checked",
                0,
            ),

            "overall_similarity": result.get(
                "overall_similarity",
                0.0,
            ),

            "exact_similarity": result.get(
                "exact_similarity",
                0.0,
            ),

            "semantic_similarity": result.get(
                "semantic_similarity",
                0.0,
            ),

            "lexical_similarity": result.get(
                "lexical_similarity",
                0.0,
            ),

            "total_matches": result.get(
                "total_matches",
                0,
            ),

            "risk_level": result.get(
                "risk_level"
            ),

            "source_results": result.get(
                "source_results",
                [],
            ),
        }

        # ----------------------------------------------------
        # 7. Create new originality report
        # ----------------------------------------------------

        report = OriginalityReport(
            project_id=project_id,

            paper_id=request.paper_id,

            overall_similarity=result.get(
                "overall_similarity",
                0.0,
            ),

            exact_similarity=result.get(
                "exact_similarity",
                0.0,
            ),

            semantic_similarity=result.get(
                "semantic_similarity",
                0.0,
            ),

            total_matches=result.get(
                "total_matches",
                0,
            ),

            potential_missing_citations=0,

            risk_level=result.get(
                "risk_level"
            ),

            report_json=report_json,
        )

        db.add(report)

        # Get report ID before creating matches
        db.flush()

        # ----------------------------------------------------
        # 8. Save similarity matches
        # ----------------------------------------------------

        matches = result.get(
            "matches",
            [],
        )

        for match in matches:

            similarity_match = SimilarityMatch(

                report_id=report.id,

                source_paper_id=match.get(
                    "source_paper_id"
                ),

                source_title=match.get(
                    "source_title"
                ),

                source_url=match.get(
                    "source_url"
                ),

                source_doi=match.get(
                    "source_doi"
                ),

                matched_text=match.get(
                    "matched_text",
                    "",
                ),

                source_text=match.get(
                    "source_text"
                ),

                similarity_score=match.get(
                    "similarity_score",
                    0.0,
                ),

                match_type=match.get(
                    "match_type",
                    "low_similarity",
                ),

                section=match.get(
                    "section"
                ),
            )

            db.add(similarity_match)

        # ----------------------------------------------------
        # 9. Commit everything
        # ----------------------------------------------------

        db.commit()

        # ----------------------------------------------------
        # 10. Refresh report
        # ----------------------------------------------------

        db.refresh(report)

        # ----------------------------------------------------
        # 11. Build API response
        # ----------------------------------------------------

        saved_matches = (
            db.query(SimilarityMatch)
            .filter(
                SimilarityMatch.report_id
                == report.id
            )
            .order_by(
                SimilarityMatch.similarity_score.desc()
            )
            .all()
        )

        match_responses = []

        for similarity_match in saved_matches:

            match_responses.append(
                SimilarityMatchResponse(
                    id=similarity_match.id,

                    source_paper_id=(
                        similarity_match.source_paper_id
                    ),

                    source_title=(
                        similarity_match.source_title
                    ),

                    source_url=(
                        similarity_match.source_url
                    ),

                    source_doi=(
                        similarity_match.source_doi
                    ),

                    matched_text=(
                        similarity_match.matched_text
                    ),

                    source_text=(
                        similarity_match.source_text
                    ),

                    similarity_score=(
                        similarity_match.similarity_score
                    ),

                    match_type=(
                        similarity_match.match_type
                    ),

                    section=(
                        similarity_match.section
                    ),
                )
            )

        # ----------------------------------------------------
        # 12. Return final response
        # ----------------------------------------------------

        return OriginalityReportResponse(

            id=report.id,

            project_id=report.project_id,

            paper_id=report.paper_id,

            overall_similarity=(
                report.overall_similarity
            ),

            exact_similarity=(
                report.exact_similarity
            ),

            semantic_similarity=(
                report.semantic_similarity
            ),

            total_matches=(
                report.total_matches
            ),

            potential_missing_citations=(
                report.potential_missing_citations
            ),

            risk_level=(
                report.risk_level
            ),

            matches=match_responses,
        )

    except HTTPException:
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Originality analysis failed: "
                f"{str(e)}"
            ),
        )