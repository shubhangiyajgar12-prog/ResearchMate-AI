from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.originality.uploaded_manuscript_service import (
    analyze_uploaded_manuscript,
)

router = APIRouter(
    prefix="/originality",
    tags=["Originality"],
)


@router.post("/projects/{project_id}/check-upload")
async def check_uploaded_manuscript(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A PDF manuscript is required.",
        )

    filename = file.filename.strip()

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF manuscripts are supported.",
        )

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty.",
        )

    if len(pdf_bytes) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="PDF is too large. Maximum allowed size is 25 MB.",
        )

    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file does not look like a valid PDF.",
        )

    try:
        return analyze_uploaded_manuscript(
            db=db,
            project_id=project_id,
            pdf_bytes=pdf_bytes,
            filename=filename,
            include_saved_project_papers=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Uploaded manuscript analysis failed: {exc}",
        ) from exc
