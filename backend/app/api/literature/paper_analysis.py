from typing import Optional, Tuple
import re

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.services.literature.pdf_analysis import analyze_pdf


router = APIRouter(
    prefix="/literature",
    tags=["Literature PDF Analysis"],
)

MAX_PDF_SIZE = 10 * 1024 * 1024
REQUEST_TIMEOUT = 6


def _is_pdf_response(response: requests.Response) -> bool:
    content_type = (response.headers.get("content-type") or "").lower()
    return (
        response.content[:4] == b"%PDF"
        or "application/pdf" in content_type
    )


def _download_pdf(url: str) -> Tuple[bytes, str]:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
        headers={
            "User-Agent": "ResearchMateAI/1.0 (academic research tool)",
            "Accept": "application/pdf,*/*",
        },
    )
    response.raise_for_status()

    content = response.content

    if len(content) > MAX_PDF_SIZE:
        raise ValueError("PDF is larger than 10 MB.")

    if not _is_pdf_response(response):
        raise ValueError("URL did not return a PDF.")

    filename = url.rstrip("/").split("/")[-1] or "paper.pdf"
    if "?" in filename:
        filename = filename.split("?", 1)[0]
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return content, filename


def _candidate_pdf_urls(paper: LiteraturePaper) -> list[str]:
    candidates: list[str] = []

    def add(url):
        if not isinstance(url, str):
            return
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return
        if url not in candidates:
            candidates.append(url)

    # Saved URL may itself be a direct PDF.
    add(paper.url)

    # OpenAlex is the primary metadata resolver because saved papers use
    # OpenAlex work IDs in paper_id in this project.
    paper_id = str(paper.paper_id or "").strip()

    if paper_id.startswith("https://openalex.org/"):
        work_url = paper_id
    elif paper_id.startswith("W") and paper_id[1:].isdigit():
        work_url = f"https://api.openalex.org/works/{paper_id}"
    else:
        work_url = None

    if work_url:
        try:
            response = requests.get(
                work_url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "ResearchMateAI/1.0"},
            )
            if response.ok:
                data = response.json()

                oa = data.get("open_access") or {}
                locations = data.get("locations") or []
                best = data.get("best_oa_location") or {}

                add(oa.get("pdf_url"))
                add(oa.get("oa_url"))

                add(best.get("pdf_url"))
                add(best.get("landing_page_url"))

                for location in locations:
                    if isinstance(location, dict):
                        add(location.get("pdf_url"))
                        add(location.get("landing_page_url"))
        except requests.RequestException:
            pass

    # Crossref fallback using DOI.
    doi = (paper.doi or "").strip()
    if doi:
        doi_url = doi
        if not doi_url.startswith("http"):
            doi_url = f"https://doi.org/{doi_url}"

        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params={"query.bibliographic": paper.title or "", "rows": 5},
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "ResearchMateAI/1.0"},
            )

            if response.ok:
                items = response.json().get("message", {}).get("items", [])
                for item in items:
                    item_doi = (item.get("DOI") or "").lower()
                    if item_doi and item_doi == doi.lower().replace("https://doi.org/", ""):
                        for link in item.get("link") or []:
                            if isinstance(link, dict):
                                add(link.get("URL"))
        except requests.RequestException:
            pass

    # Only URLs that actually respond with PDF are accepted by the resolver.
    return candidates


def _resolve_saved_paper_pdf(paper: LiteraturePaper) -> Optional[Tuple[bytes, str, str]]:
    urls = _candidate_pdf_urls(paper)

    errors = []

    for url in urls:
        try:
            content, filename = _download_pdf(url)
            return content, filename, url
        except Exception as exc:
            errors.append(str(exc))

    return None


def _save_analysis(
    db: Session,
    project_id: int,
    paper_id: int,
    filename: str,
    extracted_text: str,
    analysis: dict,
) -> PaperAnalysis:
    record = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.literature_paper_id == paper_id,
            PaperAnalysis.project_id == project_id,
        )
        .first()
    )

    if record:
        record.filename = filename
        record.extracted_text = extracted_text
        record.analysis_json = analysis
    else:
        record = PaperAnalysis(
            literature_paper_id=paper_id,
            project_id=project_id,
            filename=filename,
            extracted_text=extracted_text,
            analysis_json=analysis,
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    return record


@router.post("/projects/{project_id}/papers/{paper_id}/analyze-pdf")
async def analyze_saved_paper_pdf(
    project_id: int,
    paper_id: int,
    request: Request,
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

    source_url = None
    file = None

    # Do NOT declare UploadFile/File(...) in the route signature.
    # The frontend may intentionally send a plain POST with no multipart body
    # when it wants automatic PDF retrieval. FastAPI's File dependency would
    # reject such a request with 422 before this function executes.
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/form-data"):
        try:
            form = await request.form()
            candidate = form.get("file")
            if isinstance(candidate, UploadFile):
                file = candidate
        except Exception:
            file = None

    if file is not None and file.filename:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")

        contents = await file.read()
        filename = file.filename

        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")

        if len(contents) > MAX_PDF_SIZE:
            raise HTTPException(status_code=400, detail="PDF file size must be less than 10 MB.")

    else:
        resolved = _resolve_saved_paper_pdf(paper)
        if resolved is None:
            # This is a normal, actionable state — not an API validation error.
            # The frontend can now open its PDF picker and retry with FormData.
            return {
                "id": None,
                "analysis_id": None,
                "project_id": project_id,
                "paper_id": paper_id,
                "analysis": None,
                "has_analysis": False,
                "automatic_pdf_fetch": False,
                "manual_upload_required": True,
                "reason": "automatic_pdf_unavailable",
                "message": (
                    "No accessible full-text PDF was found for this saved paper. "
                    "Please upload the paper PDF manually to analyze it."
                ),
            }
        contents, filename, source_url = resolved

    try:
        analysis = analyze_pdf(filename, contents)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"PDF analysis failed: {exc}",
        ) from exc

    # The generic service returns the complete extracted text when available.
    extracted_text = analysis.get("extracted_text") or ""

    if not extracted_text:
        # Fallback: keep a searchable representation even if a custom
        # analyzer omitted the raw text field.
        section_text = []
        for value in (analysis.get("sections") or {}).values():
            if isinstance(value, str):
                section_text.append(value)
        for item in analysis.get("subsections") or []:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                section_text.append(item["text"])
        extracted_text = "\n\n".join(section_text)

    analysis["source"] = {
        "type": "automatic_open_access_pdf" if source_url else "manual_upload",
        "url": source_url,
    }

    record = _save_analysis(
        db=db,
        project_id=project_id,
        paper_id=paper_id,
        filename=filename,
        extracted_text=extracted_text,
        analysis=analysis,
    )

    return {
        "id": record.id,
        "analysis_id": record.id,
        "project_id": project_id,
        "paper_id": paper_id,
        "filename": record.filename,
        "extracted_text_length": len(record.extracted_text or ""),
        "analysis": record.analysis_json,
        "has_analysis": True,
        "source_url": source_url,
        "automatic_pdf_fetch": bool(source_url),
    }


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
        .filter(
            PaperAnalysis.literature_paper_id == paper_id,
            PaperAnalysis.project_id == project_id,
        )
        .order_by(PaperAnalysis.id.desc())
        .first()
    )

    # Absence of analysis is a valid state for a saved paper.
    # Return 200 so the Literature page does not fill the backend log with
    # expected 404 responses.
    if not record:
        return {
            "id": None,
            "analysis_id": None,
            "project_id": project_id,
            "paper_id": paper_id,
            "filename": None,
            "extracted_text_length": 0,
            "analysis": None,
            "has_analysis": False,
            "source_url": None,
            "automatic_pdf_fetch": False,
        }

    source = record.analysis_json.get("source", {}) if isinstance(
        record.analysis_json, dict
    ) else {}

    return {
        "id": record.id,
        "analysis_id": record.id,
        "project_id": project_id,
        "paper_id": paper_id,
        "filename": record.filename,
        "extracted_text_length": len(record.extracted_text or ""),
        "analysis": record.analysis_json,
        "has_analysis": True,
        "source_url": source.get("url"),
        "automatic_pdf_fetch": source.get("type") == "automatic_open_access_pdf",
    }
