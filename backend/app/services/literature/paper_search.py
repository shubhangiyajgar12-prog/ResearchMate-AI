import httpx

from app.schemas.literature.paper import (
    PaperAuthor,
    PaperResult,
    PaperSearchResponse,
)


SEMANTIC_SCHOLAR_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)

OPENALEX_URL = "https://api.openalex.org/works"


# ==================================================
# SEMANTIC SCHOLAR SEARCH
# ==================================================

def search_semantic_scholar(
    query: str,
    limit: int
) -> PaperSearchResponse:

    params = {
        "query": query,
        "limit": limit,
        "fields": (
            "paperId,title,abstract,year,authors,"
            "citationCount,url,externalIds"
        ),
    }

    response = httpx.get(
        SEMANTIC_SCHOLAR_URL,
        params=params,
        timeout=20.0,
    )

    response.raise_for_status()

    data = response.json()

    papers = []

    for paper in data.get("data", []):

        authors = []

        for author in paper.get("authors", []):
            author_name = author.get("name")

            if author_name:
                authors.append(
                    PaperAuthor(name=author_name)
                )

        external_ids = paper.get("externalIds") or {}

        doi = external_ids.get("DOI")

        papers.append(
            PaperResult(
                paper_id=paper.get("paperId"),
                title=paper.get("title") or "Untitled Paper",
                abstract=paper.get("abstract"),
                year=paper.get("year"),
                authors=authors,
                citation_count=paper.get("citationCount"),
                url=paper.get("url"),
                doi=doi,
            )
        )

    return PaperSearchResponse(
        query=query,
        total=data.get("total", len(papers)),
        papers=papers,
        source="Semantic Scholar",
    )


# ==================================================
# OPENALEX FALLBACK SEARCH
# ==================================================

def search_openalex(
    query: str,
    limit: int
) -> PaperSearchResponse:

    params = {
        "search": query,
        "per-page": limit,
    }

    response = httpx.get(
        OPENALEX_URL,
        params=params,
        timeout=20.0,
    )

    response.raise_for_status()

    data = response.json()

    papers = []

    for work in data.get("results", []):

        authors = []

        for authorship in work.get("authorships", []):

            author = authorship.get("author") or {}

            author_name = author.get("display_name")

            if author_name:
                authors.append(
                    PaperAuthor(name=author_name)
                )

        doi = work.get("doi")

        if doi:
            doi = doi.replace(
                "https://doi.org/",
                ""
            )

        primary_location = (
            work.get("primary_location") or {}
        )

        landing_page = (
            primary_location.get("landing_page_url")
        )

        paper_url = landing_page or work.get("id")

        abstract = None

        # OpenAlex stores abstracts as inverted indexes.
        abstract_inverted_index = (
            work.get("abstract_inverted_index")
        )

        if abstract_inverted_index:

            words = []

            for word, positions in (
                abstract_inverted_index.items()
            ):
                for position in positions:
                    words.append((position, word))

            words.sort(key=lambda item: item[0])

            abstract = " ".join(
                word for _, word in words
            )

        papers.append(
            PaperResult(
                paper_id=work.get("id"),
                title=work.get("display_name")
                or "Untitled Paper",
                abstract=abstract,
                year=work.get("publication_year"),
                authors=authors,
                citation_count=work.get("cited_by_count"),
                url=paper_url,
                doi=doi,
            )
        )

    return PaperSearchResponse(
        query=query,
        total=data.get("meta", {}).get(
            "count",
            len(papers)
        ),
        papers=papers,
        source="OpenAlex",
    )


# ==================================================
# MAIN SEARCH FUNCTION
# ==================================================

def search_academic_papers(
    query: str,
    limit: int = 10
) -> PaperSearchResponse:

    try:

        return search_semantic_scholar(
            query=query,
            limit=limit
        )

    except httpx.HTTPStatusError as error:

        status_code = error.response.status_code

        # Semantic Scholar rate limit
        if status_code == 429:

            print(
                "Semantic Scholar rate limit reached."
                " Switching to OpenAlex..."
            )

            return search_openalex(
                query=query,
                limit=limit
            )

        # Other Semantic Scholar errors
        print(
            f"Semantic Scholar error {status_code}."
            " Switching to OpenAlex..."
        )

        return search_openalex(
            query=query,
            limit=limit
        )

    except httpx.RequestError as error:

        print(
            f"Semantic Scholar connection error: {error}"
        )

        return search_openalex(
            query=query,
            limit=limit
        )