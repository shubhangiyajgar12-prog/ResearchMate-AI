from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.services.literature.pdf_analysis import analyze_pdf


router = APIRouter(prefix="/literature", tags=["Literature Intelligence"])

MAX_PDF_SIZE = 10 * 1024 * 1024


@router.post("/projects/{project_id}/papers/{paper_id}/analyze-pdf")
async def analyze_saved_paper_pdf(
    project_id: int,
    paper_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id,
        )
        .first()
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Saved paper not found in this research project.",
        )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    contents = await file.read()

    if len(contents) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail="PDF file size must be less than 10 MB.",
        )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty.",
        )

    try:
        analysis = analyze_pdf(file.filename, contents)

        existing = (
            db.query(PaperAnalysis)
            .filter(PaperAnalysis.literature_paper_id == paper_id)
            .first()
        )

        if existing:
            existing.project_id = project_id
            existing.filename = file.filename
            existing.analysis_json = analysis
            analysis_record = existing
        else:
            analysis_record = PaperAnalysis(
                literature_paper_id=paper_id,
                project_id=project_id,
                filename=file.filename,
                analysis_json=analysis,
            )
            db.add(analysis_record)

        db.commit()
        db.refresh(analysis_record)

        return {
            "analysis_id": analysis_record.id,
            "project_id": project_id,
            "paper_id": paper_id,
            "filename": file.filename,
            "analysis": analysis,
        }

    except HTTPException:
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Saved paper PDF analysis failed: {str(error)}",
        )


@router.get("/projects/{project_id}/papers/{paper_id}/analysis")
def get_saved_paper_analysis(
    project_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
):
    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id,
        )
        .first()
    )

    if not paper:
        raise HTTPException(
            status_code=404,
            detail="Saved paper not found in this research project.",
        )

    record = (
        db.query(PaperAnalysis)
        .filter(PaperAnalysis.literature_paper_id == paper_id)
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=404,
            detail="No PDF analysis is available for this saved paper yet.",
        )

    return {
        "analysis_id": record.id,
        "project_id": project_id,
        "paper_id": paper_id,
        "filename": record.filename,
        "analysis": record.analysis_json,
    }
