from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db

from app.models.literature_paper import LiteraturePaper
from app.models.originality_reports import OriginalityReport
from app.models.citation_analysis import CitationAnalysis

from app.schemas.originality.similarity import (
    OriginalityAnalysisRequest,
)

from app.schemas.originality.citation import (
    CitationAnalysisResponse,
    CitationFinding,
)

from app.services.originality.citation_service import (
    analyze_citations,
)


router = APIRouter(
    prefix="/originality",
    tags=["Originality & Citations"],
)


# ============================================================
# CITATION ANALYSIS
# ============================================================

@router.post(
    "/projects/{project_id}/citation-analysis",
    response_model=CitationAnalysisResponse,
)
def run_citation_analysis(
    project_id: int,
    request: OriginalityAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        # ----------------------------------------------------
        # 1. Validate project ID
        # ----------------------------------------------------
        if request.project_id != project_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "project_id in request body does not "
                    "match project_id in URL."
                ),
            )

        # ----------------------------------------------------
        # 2. Validate paper
        # ----------------------------------------------------
        paper = (
            db.query(LiteraturePaper)
            .filter(
                LiteraturePaper.id == request.paper_id,
                LiteraturePaper.project_id == project_id,
            )
            .first()
        )

        if not paper:
            raise HTTPException(
                status_code=404,
                detail="Paper not found for this project.",
            )

        # ----------------------------------------------------
        # 3. Confirm that an originality report exists BEFORE
        #    running citation analysis.
        #
        #    We only use this as a validation check here.
        #    We intentionally DO NOT keep this ORM object for
        #    later inserts because analyze_citations() may use
        #    its own transaction/session state.
        # ----------------------------------------------------
        existing_report = (
            db.query(OriginalityReport)
            .filter(
                OriginalityReport.project_id == project_id,
                OriginalityReport.paper_id == request.paper_id,
            )
            .order_by(OriginalityReport.id.desc())
            .first()
        )

        if not existing_report:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Originality analysis not found. "
                    "Run similarity analysis first."
                ),
            )

        # Store the ID only for diagnostics/validation.
        existing_report_id = existing_report.id

        # ----------------------------------------------------
        # 4. Run citation analysis
        #
        # IMPORTANT:
        # Do this BEFORE loading the report object that will
        # receive CitationAnalysis rows. The citation service
        # can change/commit the current transaction.
        # ----------------------------------------------------
        result = analyze_citations(
            db=db,
            project_id=project_id,
            paper_id=request.paper_id,
        )

        # ----------------------------------------------------
        # 5. Re-query the report AFTER analyze_citations()
        #
        # This fixes the ForeignKeyViolation where an ORM
        # object from the previous transaction was being used
        # after the citation service changed the transaction.
        # ----------------------------------------------------
        report = (
            db.query(OriginalityReport)
            .filter(
                OriginalityReport.project_id == project_id,
                OriginalityReport.paper_id == request.paper_id,
            )
            .order_by(OriginalityReport.id.desc())
            .first()
        )

        if not report:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Citation analysis completed, but the "
                    "corresponding originality report could not "
                    "be found after the analysis transaction."
                ),
            )

        # ----------------------------------------------------
        # 6. Verify that the report really exists in the DB
        # before inserting child CitationAnalysis rows.
        # ----------------------------------------------------
        report_exists = (
            db.query(OriginalityReport.id)
            .filter(OriginalityReport.id == report.id)
            .first()
        )

        if not report_exists:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Originality report {report.id} is not "
                    "available in the database."
                ),
            )

        # ----------------------------------------------------
        # 7. Delete previous citation findings for THIS report
        # ----------------------------------------------------
        (
            db.query(CitationAnalysis)
            .filter(
                CitationAnalysis.report_id == report.id
            )
            .delete(
                synchronize_session=False
            )
        )

        db.flush()

        # ----------------------------------------------------
        # 8. Save new findings
        # ----------------------------------------------------
        saved_findings = []

        for finding in result.get("findings", []):
            citation_finding = CitationAnalysis(
                report_id=report.id,
                section=finding.get("section"),
                claim_text=finding.get(
                    "claim_text",
                    "",
                ),
                citation_present=finding.get(
                    "citation_present",
                    "no",
                ),
                citation_needed=finding.get(
                    "citation_needed",
                    "yes",
                ),
                confidence=finding.get(
                    "confidence"
                ),
                suggested_source_id=finding.get(
                    "suggested_source_id"
                ),
                suggestion_reason=finding.get(
                    "suggestion_reason"
                ),
            )

            db.add(citation_finding)
            saved_findings.append(citation_finding)

        # Flush so FK/DB errors happen here, before commit.
        db.flush()

        # ----------------------------------------------------
        # 9. Update originality report
        # ----------------------------------------------------
        report.potential_missing_citations = result.get(
            "potential_missing_citations",
            0,
        )

        report_json = (
            report.report_json
            if isinstance(report.report_json, dict)
            else {}
        )

        report_json["citation_analysis"] = {
            "total_claims": result.get(
                "total_claims",
                0,
            ),
            "citations_present": result.get(
                "citations_present",
                0,
            ),
            "potential_missing_citations": result.get(
                "potential_missing_citations",
                0,
            ),
            "citation_coverage": result.get(
                "citation_coverage",
                0.0,
            ),
        }

        report.report_json = report_json

        # ----------------------------------------------------
        # 10. Commit EVERYTHING together
        # ----------------------------------------------------
        db.commit()

        # ----------------------------------------------------
        # 11. Refresh report after commit
        # ----------------------------------------------------
        db.refresh(report)

        # ----------------------------------------------------
        # 12. Build response
        # ----------------------------------------------------
        response_findings = []

        raw_findings = result.get(
            "findings",
            [],
        )

        for index, finding in enumerate(saved_findings):
            raw = (
                raw_findings[index]
                if index < len(raw_findings)
                else {}
            )

            response_findings.append(
                CitationFinding(
                    id=finding.id,
                    section=finding.section,
                    claim_text=finding.claim_text,
                    claim_type=raw.get(
                        "claim_type"
                    ),
                    citation_present=finding.citation_present,
                    citation_needed=finding.citation_needed,
                    citation_status=raw.get(
                        "citation_status"
                    ),
                    confidence=finding.confidence,
                    suggested_source_id=(
                        finding.suggested_source_id
                    ),
                    suggestion_reason=(
                        finding.suggestion_reason
                    ),
                )
            )

        return CitationAnalysisResponse(
            report_id=report.id,
            citation_coverage=result.get(
                "citation_coverage",
                0.0,
            ),
            total_claims=result.get(
                "total_claims",
                0,
            ),
            citations_present=result.get(
                "citations_present",
                0,
            ),
            potential_missing_citations=result.get(
                "potential_missing_citations",
                0,
            ),

            citation_required_claims=result.get(
                "citation_required_claims",
                0,
            ),

            cited_required_claims=result.get(
                "cited_required_claims",
                0,
            ),

            own_research_claims=result.get(
                "own_research_claims",
                0,
            ),

            inherited_context_claims=result.get(
                "inherited_context_claims",
                0,
            ),

            ignored_artifacts=result.get(
                "ignored_artifacts",
                0,
            ),

            risk_level=result.get(
                "risk_level"
            ),

            findings=response_findings,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Citation analysis failed: "
                f"{str(e)}"
            ),
        )
