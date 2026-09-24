from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.originality.uploaded_manuscript_service import (
    analyze_uploaded_manuscript,
)

router = APIRouter(prefix="/originality", tags=["Originality"])


@router.post("/projects/{project_id}/check-upload")
async def check_uploaded_manuscript(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise ValueError("A PDF manuscript is required.")

    if not file.filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF manuscripts are supported.")

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise ValueError("Uploaded PDF is empty.")

    if len(pdf_bytes) > 25 * 1024 * 1024:
        raise ValueError("PDF is too large. Maximum allowed size is 25 MB.")

    return analyze_uploaded_manuscript(
        db=db,
        project_id=project_id,
        pdf_bytes=pdf_bytes,
        filename=file.filename,
        include_saved_project_papers=True,
    )