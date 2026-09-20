import httpx

from app.schemas.literature.paper import (
    PaperAuthor,
    PaperResult,
    PaperSearchResponse,
)


SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search_academic_papers(query: str, limit: int = 10) -> PaperSearchResponse:

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,abstract,citationCount,url,externalIds",
    }

    try:
        response = httpx.get(
            SEMANTIC_SCHOLAR_URL,
            params=params,
            timeout=20.0,
        )

        response.raise_for_status()

        data = response.json()

    except httpx.HTTPError as error:
        raise RuntimeError(
            f"Unable to fetch papers from Semantic Scholar: {error}"
        )

    papers = []

    for paper in data.get("data", []):

        authors = [
            PaperAuthor(name=author.get("name", "Unknown Author"))
            for author in paper.get("authors", [])
        ]

        external_ids = paper.get("externalIds") or {}

        paper_result = PaperResult(
            paper_id=paper.get("paperId"),
            title=paper.get("title") or "Untitled Paper",
            abstract=paper.get("abstract"),
            year=paper.get("year"),
            authors=authors,
            citation_count=paper.get("citationCount"),
            url=paper.get("url"),
            doi=external_ids.get("DOI"),
        )

        papers.append(paper_result)

    return PaperSearchResponse(
        query=query,
        total=data.get("total", len(papers)),
        papers=papers,
        source="Semantic Scholar",
    )