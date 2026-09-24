from fastapi import APIRouter, HTTPException, Query
import asyncio
import html
import re
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


OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"

OPENALEX_EMAIL = "researchmate.ai@gmail.com"

MAX_RETRIES = 2
REQUEST_TIMEOUT = 30.0


# ============================================================
# Helpers
# ============================================================

def _reconstruct_abstract(inverted_index):
    if not inverted_index:
        return None

    words = []

    for word, positions in inverted_index.items():
        for position in positions:
            words.append((position, word))

    words.sort(key=lambda item: item[0])

    return " ".join(word for _, word in words)


def _clean_abstract(value):
    if not value:
        return None

    value = html.unescape(value)

    # Remove HTML tags from Crossref abstracts
    value = re.sub(r"<[^>]+>", " ", value)

    # Normalize whitespace
    value = re.sub(r"\s+", " ", value)

    return value.strip() or None


def _normalize_doi(doi):
    if not doi:
        return None

    doi = doi.strip()

    doi = re.sub(
        r"^https?://doi\.org/",
        "",
        doi,
        flags=re.IGNORECASE,
    )

    doi = re.sub(
        r"^doi:",
        "",
        doi,
        flags=re.IGNORECASE,
    )

    return doi.strip() or None


def _doi_url(doi):
    doi = _normalize_doi(doi)

    if not doi:
        return None

    return f"https://doi.org/{doi}"


def _normalize_title(title):
    if not title:
        return ""

    return re.sub(
        r"\s+",
        " ",
        title.lower().strip(),
    )


def _extract_year_from_crossref(item):
    for field in (
        "published-print",
        "published-online",
        "published",
        "issued",
        "created",
    ):
        date_data = item.get(field) or {}
        date_parts = date_data.get("date-parts") or []

        if date_parts and date_parts[0]:
            year = date_parts[0][0]

            if isinstance(year, int):
                return year

    return None


# ============================================================
# OpenAlex
# ============================================================

async def _search_openalex(
    query: str,
    limit: int,
    page: int,
):
    headers = {
        "User-Agent": (
            "ResearchMate-AI/1.0 "
            f"(mailto:{OPENALEX_EMAIL})"
        ),
        "Accept": "application/json",
    }

    params = {
        "search": query,
        "per-page": limit,
        "page": page,
        "mailto": OPENALEX_EMAIL,
    }

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:

        for attempt in range(MAX_RETRIES + 1):

            try:
                response = await client.get(
                    OPENALEX_URL,
                    params=params,
                )

                if response.status_code == 429:

                    if attempt < MAX_RETRIES:

                        retry_after = response.headers.get(
                            "Retry-After"
                        )

                        try:
                            wait_seconds = float(
                                retry_after
                            ) if retry_after else 3.0
                        except ValueError:
                            wait_seconds = 3.0

                        await asyncio.sleep(
                            min(wait_seconds, 10.0)
                        )

                        continue

                    raise RuntimeError(
                        "OpenAlex rate limit exceeded"
                    )

                if response.status_code in {
                    500,
                    502,
                    503,
                    504,
                }:

                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2)
                        continue

                    raise RuntimeError(
                        f"OpenAlex server error "
                        f"{response.status_code}"
                    )

                response.raise_for_status()

                return response.json()

            except (
                httpx.TimeoutException,
                httpx.RequestError,
            ) as error:

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2)
                    continue

                raise RuntimeError(
                    f"OpenAlex connection error: {error}"
                ) from error


# ============================================================
# Crossref
# ============================================================

async def _search_crossref(
    query: str,
    limit: int,
    page: int,
):
    """
    Crossref fallback provider.

    Crossref pagination uses:
        offset + rows
    """

    offset = (page - 1) * limit

    headers = {
        "User-Agent": (
            "ResearchMate-AI/1.0 "
            f"(mailto:{OPENALEX_EMAIL})"
        ),
        "Accept": "application/json",
    }

    params = {
        "query": query,
        "rows": limit,
        "offset": offset,
        "mailto": OPENALEX_EMAIL,
    }

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:

        for attempt in range(MAX_RETRIES + 1):

            try:
                response = await client.get(
                    CROSSREF_URL,
                    params=params,
                )

                if response.status_code == 429:

                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(3)
                        continue

                    raise RuntimeError(
                        "Crossref rate limit exceeded"
                    )

                if response.status_code in {
                    500,
                    502,
                    503,
                    504,
                }:

                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(2)
                        continue

                    raise RuntimeError(
                        f"Crossref server error "
                        f"{response.status_code}"
                    )

                response.raise_for_status()

                return response.json()

            except (
                httpx.TimeoutException,
                httpx.RequestError,
            ) as error:

                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2)
                    continue

                raise RuntimeError(
                    f"Crossref connection error: {error}"
                ) from error


# ============================================================
# OpenAlex normalization
# ============================================================

def _normalize_openalex_results(data):
    papers = []

    for work in data.get("results", []):

        openalex_id = work.get("id")

        paper_id = (
            openalex_id.rstrip("/").split("/")[-1]
            if openalex_id
            else None
        )

        authors = []

        for authorship in work.get(
            "authorships",
            [],
        ):

            author = authorship.get(
                "author"
            ) or {}

            name = author.get(
                "display_name"
            )

            if name:
                authors.append(
                    PaperAuthor(
                        name=name
                    )
                )

        primary_location = (
            work.get("primary_location")
            or {}
        )

        landing_page_url = (
            primary_location.get(
                "landing_page_url"
            )
        )

        doi = _normalize_doi(
            work.get("doi")
        )

        url = (
            landing_page_url
            or _doi_url(doi)
        )

        papers.append(
            PaperResult(
                paper_id=paper_id,
                title=(
                    work.get("display_name")
                    or work.get("title")
                    or "Untitled paper"
                ),
                abstract=_reconstruct_abstract(
                    work.get(
                        "abstract_inverted_index"
                    )
                ),
                year=work.get(
                    "publication_year"
                ),
                authors=authors,
                citation_count=work.get(
                    "cited_by_count",
                    0,
                ) or 0,
                url=url,
                doi=doi,
            )
        )

    return papers


# ============================================================
# Crossref normalization
# ============================================================

def _normalize_crossref_results(data):
    papers = []

    message = data.get("message") or {}

    items = message.get("items") or []

    for item in items:

        titles = item.get("title") or []

        title = (
            titles[0]
            if titles
            else "Untitled paper"
        )

        authors = []

        for author in item.get(
            "author",
            [],
        ):

            given = (
                author.get("given")
                or ""
            ).strip()

            family = (
                author.get("family")
                or ""
            ).strip()

            full_name = (
                f"{given} {family}"
            ).strip()

            if full_name:
                authors.append(
                    PaperAuthor(
                        name=full_name
                    )
                )

        doi = _normalize_doi(
            item.get("DOI")
        )

        url = (
            item.get("URL")
            or _doi_url(doi)
        )

        citation_count = item.get(
            "is-referenced-by-count",
            0,
        ) or 0

        year = _extract_year_from_crossref(
            item
        )

        abstract = _clean_abstract(
            item.get("abstract")
        )

        # Crossref ID:
        # Prefer DOI, otherwise URL.
        paper_id = (
            f"crossref:{doi}"
            if doi
            else (
                f"crossref:{url}"
                if url
                else None
            )
        )

        papers.append(
            PaperResult(
                paper_id=paper_id,
                title=title,
                abstract=abstract,
                year=year,
                authors=authors,
                citation_count=citation_count,
                url=url,
                doi=doi,
            )
        )

    return papers


# ============================================================
# Deduplication
# ============================================================

def _deduplicate_papers(papers):
    unique = []

    seen_dois = set()
    seen_titles = set()

    for paper in papers:

        doi = _normalize_doi(
            paper.doi
        )

        title_key = _normalize_title(
            paper.title
        )

        if doi:

            if doi.lower() in seen_dois:
                continue

            seen_dois.add(
                doi.lower()
            )

        elif title_key:

            if title_key in seen_titles:
                continue

            seen_titles.add(
                title_key
            )

        unique.append(paper)

    return unique


# ============================================================
# Search endpoint
# ============================================================

@router.get(
    "/search",
    response_model=PaperSearchResponse,
)
async def search_papers(
    query: str = Query(
        ...,
        min_length=3,
        max_length=300,
    ),
    limit: int = Query(
        10,
        ge=1,
        le=20,
    ),
    page: int = Query(
        1,
        ge=1,
    ),
):

    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty.",
        )

    openalex_error = None

    # ========================================================
    # 1. Try OpenAlex
    # ========================================================

    try:

        data = await _search_openalex(
            query=query,
            limit=limit,
            page=page,
        )

        papers = _normalize_openalex_results(
            data
        )

        if papers:

            meta = data.get("meta") or {}

            return PaperSearchResponse(
                query=query,
                total=meta.get(
                    "count",
                    len(papers),
                ),
                papers=papers,
                source="OpenAlex",
            )

    except Exception as error:

        openalex_error = str(error)

    # ========================================================
    # 2. OpenAlex unavailable → Crossref
    # ========================================================

    try:

        data = await _search_crossref(
            query=query,
            limit=limit,
            page=page,
        )

        papers = _normalize_crossref_results(
            data
        )

        papers = _deduplicate_papers(
            papers
        )

        message = data.get(
            "message"
        ) or {}

        total = message.get(
            "total-results",
            len(papers),
        )

        return PaperSearchResponse(
            query=query,
            total=total,
            papers=papers,
            source="Crossref",
        )

    except Exception as crossref_error:

        raise HTTPException(
            status_code=502,
            detail=(
                "Academic search providers are "
                "temporarily unavailable. "
                f"OpenAlex: {openalex_error or 'unavailable'}. "
                f"Crossref: {crossref_error}"
            ),
        ) from crossref_error


# ============================================================
# Saved project papers
# ============================================================

@router.get(
    "/projects/{project_id}/papers"
)
def get_saved_project_papers(
    project_id: int,
):

    from app.database.database import SessionLocal
    from app.models.literature_paper import LiteraturePaper

    db = SessionLocal()

    try:

        rows = (
            db.query(LiteraturePaper)
            .filter(
                LiteraturePaper.project_id
                == project_id
            )
            .order_by(
                LiteraturePaper.id.desc()
            )
            .all()
        )

        return [
            {
                "id": paper.id,
                "project_id": paper.project_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "year": paper.year,
                "authors": paper.authors,
                "url": paper.url,
                "doi": paper.doi,
            }
            for paper in rows
        ]

    finally:
        db.close()