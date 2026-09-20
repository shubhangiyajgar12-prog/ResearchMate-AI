from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis
from app.schemas.literature.literature_matrix import (
    LiteraturePaperCreate,
    LiteraturePaperResponse,
    LiteratureMatrixRequest,
    LiteratureMatrixResponse,
)
from app.services.literature.literature_matrix import generate_literature_matrix


router = APIRouter(prefix="/literature", tags=["Literature Intelligence"])


@router.post(
    "/projects/{project_id}/papers",
    response_model=LiteraturePaperResponse,
)
def save_paper_to_project(
    project_id: int,
    paper: LiteraturePaperCreate,
    db: Session = Depends(get_db),
):
    if paper.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id in the request body must match the URL project_id.",
        )

    existing = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id,
            LiteraturePaper.paper_id == paper.paper_id,
        )
        .first()
    )

    if existing:
        return {
            "id": existing.id,
            "project_id": existing.project_id,
            "paper_id": existing.paper_id,
            "title": existing.title,
            "abstract": existing.abstract,
            "year": existing.year,
            "authors": [
                item.strip()
                for item in (existing.authors or "").split(",")
                if item.strip()
            ],
            "citation_count": existing.citation_count,
            "url": existing.url,
            "doi": existing.doi,
        }

    record = LiteraturePaper(
        project_id=project_id,
        paper_id=paper.paper_id,
        title=paper.title,
        abstract=paper.abstract,
        year=paper.year,
        authors=", ".join(paper.authors),
        citation_count=paper.citation_count,
        url=paper.url,
        doi=paper.doi,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "project_id": record.project_id,
        "paper_id": record.paper_id,
        "title": record.title,
        "abstract": record.abstract,
        "year": record.year,
        "authors": [
            item.strip()
            for item in (record.authors or "").split(",")
            if item.strip()
        ],
        "citation_count": record.citation_count,
        "url": record.url,
        "doi": record.doi,
    }


@router.get(
    "/projects/{project_id}/papers",
    response_model=list[LiteraturePaperResponse],
)
def get_project_papers(
    project_id: int,
    db: Session = Depends(get_db),
):
    papers = (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == project_id)
        .order_by(LiteraturePaper.created_at.desc())
        .all()
    )

    return [
        {
            "id": paper.id,
            "project_id": paper.project_id,
            "paper_id": paper.paper_id,
            "title": paper.title,
            "abstract": paper.abstract,
            "year": paper.year,
            "authors": [
                item.strip()
                for item in (paper.authors or "").split(",")
                if item.strip()
            ],
            "citation_count": paper.citation_count,
            "url": paper.url,
            "doi": paper.doi,
        }
        for paper in papers
    ]


@router.delete("/projects/{project_id}/papers/{paper_id}")
def delete_project_paper(
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

    db.delete(paper)
    db.commit()

    return {
        "message": "Paper removed from the project.",
        "paper_id": paper_id,
    }


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
            detail="Select at least one saved paper.",
        )

    papers = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == request.project_id,
            LiteraturePaper.id.in_(request.paper_ids),
        )
        .all()
    )

    paper_by_id = {paper.id: paper for paper in papers}
    missing_ids = [
        paper_id for paper_id in request.paper_ids if paper_id not in paper_by_id
    ]

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Saved paper(s) not found in project: {missing_ids}",
        )

    ordered_papers = [paper_by_id[paper_id] for paper_id in request.paper_ids]

    paper_data = []

    for paper in ordered_papers:
        authors = [
            item.strip()
            for item in (paper.authors or "").split(",")
            if item.strip()
        ]

        analysis_record = (
            db.query(PaperAnalysis)
            .filter(PaperAnalysis.literature_paper_id == paper.id)
            .first()
        )

        paper_data.append(
            {
                "id": paper.id,
                "title": paper.title,
                "abstract": paper.abstract,
                "year": paper.year,
                "authors": authors,
                "analysis": analysis_record.analysis_json
                if analysis_record
                else {},
            }
        )

    try:
        result = generate_literature_matrix(
            project_id=request.project_id,
            papers=paper_data,
        )
        return result
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Literature matrix generation failed: {str(error)}",
        )
