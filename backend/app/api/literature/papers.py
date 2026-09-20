from fastapi import APIRouter, HTTPException, Query
import httpx

from app.schemas.literature.paper import (
    PaperAuthor,
    PaperResult,
    PaperSearchResponse,
)

router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"],
)


def _reconstruct_abstract(inverted_index):
    if not inverted_index:
        return None

    words = []

    for word, positions in inverted_index.items():
        for position in positions:
            words.append((position, word))

    words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in words)


@router.get(
    "/search",
    response_model=PaperSearchResponse,
)
async def search_papers(
    query: str = Query(..., min_length=3, max_length=300),
    limit: int = Query(10, ge=1, le=20),
    page: int = Query(1, ge=1),
):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.openalex.org/works",
                params={
                    "search": query,
                    "per-page": limit,
                    "page": page,
                },
            )

        response.raise_for_status()
        data = response.json()

        papers = []

        for work in data.get("results", []):
            openalex_id = work.get("id")
            paper_id = (
                openalex_id.rstrip("/").split("/")[-1]
                if openalex_id
                else None
            )

            authors = []

            for authorship in work.get("authorships", []):
                author = authorship.get("author") or {}
                name = author.get("display_name")

                if name:
                    authors.append(PaperAuthor(name=name))

            primary_location = work.get("primary_location") or {}
            landing_page_url = primary_location.get("landing_page_url")

            doi = work.get("doi")

            papers.append(
                PaperResult(
                    paper_id=paper_id,
                    title=work.get("display_name")
                    or work.get("title")
                    or "Untitled paper",
                    abstract=_reconstruct_abstract(
                        work.get("abstract_inverted_index")
                    ),
                    year=work.get("publication_year"),
                    authors=authors,
                    citation_count=work.get("cited_by_count", 0),
                    url=landing_page_url or doi,
                    doi=doi,
                )
            )

        return PaperSearchResponse(
            query=query,
            total=(data.get("meta") or {}).get("count", len(papers)),
            papers=papers,
            source="OpenAlex",
        )

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Academic search service error: {error.response.status_code}",
        )

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to reach academic search service: {error}",
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Literature search failed: {error}",
        )
