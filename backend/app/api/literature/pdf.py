from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.literature.pdf_analysis import analyze_pdf
from app.schemas.literature.pdf_analysis import PDFAnalysisResponse


router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"]
)


# ==================================================
# PDF ANALYSIS
# ==================================================

@router.post(
    "/analyze-pdf",
    response_model=PDFAnalysisResponse
)
async def analyze_research_pdf(
    file: UploadFile = File(...)
):

    # --------------------------------------------------
    # Validate file type
    # --------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # --------------------------------------------------
    # Read file
    # --------------------------------------------------

    try:

        file_bytes = await file.read()

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Unable to read uploaded file: {error}"
        )

    # --------------------------------------------------
    # Validate file size
    # Maximum: 10 MB
    # --------------------------------------------------

    max_file_size = 10 * 1024 * 1024

    if len(file_bytes) > max_file_size:

        raise HTTPException(
            status_code=400,
            detail="PDF file size must be less than 10 MB."
        )

    if len(file_bytes) == 0:

        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty."
        )

    # --------------------------------------------------
    # Analyze PDF
    # --------------------------------------------------

    try:

        result = analyze_pdf(
            filename=file.filename,
            file_bytes=file_bytes
        )

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"PDF analysis failed: {error}"
        )