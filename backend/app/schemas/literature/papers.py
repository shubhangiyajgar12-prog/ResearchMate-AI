from fastapi import APIRouter, HTTPException, Query

from app.schemas.literature.paper import PaperSearchResponse
from app.services.literature.paper_search import search_academic_papers


router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"]
)


@router.get("/search", response_model=PaperSearchResponse)
def search_papers(
    query: str = Query(..., min_length=3, max_length=300),
    limit: int = Query(default=10, ge=1, le=20)
):
    try:
        return search_academic_papers(query, limit)

    except RuntimeError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error)
        )