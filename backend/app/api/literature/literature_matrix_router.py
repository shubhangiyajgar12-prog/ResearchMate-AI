from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.schemas.literature.literature_matrix import (
    LiteraturePaperCreate,
    LiteraturePaperResponse,
    LiteratureMatrixRequest,
    LiteratureMatrixResponse,
)
from app.services.literature.literature_matrix import generate_literature_matrix


router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"],
)


@router.post(
    "/projects/{project_id}/papers",
    response_model=LiteraturePaperResponse,
)
def save_literature_paper(
    project_id: int,
    request: LiteraturePaperCreate,
    db: Session = Depends(get_db),
):
    if request.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id in URL and request body must match.",
        )

    existing = None

    if request.paper_id:
        existing = (
            db.query(LiteraturePaper)
            .filter(
                LiteraturePaper.project_id == project_id,
                LiteraturePaper.paper_id == request.paper_id,
            )
            .first()
        )

    if existing:
        return existing

    paper = LiteraturePaper(
        project_id=project_id,
        paper_id=request.paper_id,
        title=request.title,
        abstract=request.abstract,
        year=request.year,
        authors=", ".join(request.authors),
        citation_count=request.citation_count,
        url=request.url,
        doi=request.doi,
    )

    db.add(paper)
    db.commit()
    db.refresh(paper)

    return paper


@router.get(
    "/projects/{project_id}/papers",
    response_model=list[LiteraturePaperResponse],
)
def get_project_literature(
    project_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == project_id)
        .order_by(LiteraturePaper.year.desc().nullslast(), LiteraturePaper.id.desc())
        .all()
    )


@router.delete("/projects/{project_id}/papers/{paper_id}")
def delete_project_paper(
    project_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
):
    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id,
            LiteraturePaper.id == paper_id,
        )
        .first()
    )

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    db.delete(paper)
    db.commit()

    return {"message": "Paper removed from literature library."}


@router.post(
    "/literature-matrix",
    response_model=LiteratureMatrixResponse,
)
def create_literature_matrix(
    request: LiteratureMatrixRequest,
    db: Session = Depends(get_db),
):
    if not request.paper_ids:
        raise HTTPException(
            status_code=400,
            detail="Select at least one paper.",
        )

    papers = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == request.project_id,
            LiteraturePaper.id.in_(request.paper_ids),
        )
        .all()
    )

    if len(papers) != len(set(request.paper_ids)):
        raise HTTPException(
            status_code=400,
            detail="One or more selected papers do not belong to this project.",
        )

    paper_data = [
        {
            "id": paper.id,
            "title": paper.title,
            "abstract": paper.abstract,
            "year": paper.year,
            "authors": [
                author.strip()
                for author in (paper.authors or "").split(",")
                if author.strip()
            ],
        }
        for paper in papers
    ]

    try:
        return generate_literature_matrix(
            project_id=request.project_id,
            papers=paper_data,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Literature matrix generation failed: {error}",
        )
