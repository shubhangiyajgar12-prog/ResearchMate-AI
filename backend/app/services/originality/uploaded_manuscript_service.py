from __future__ import annotations

import io
import re
from typing import Dict, List, Optional

import httpx
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.services.originality.citation_service import clean_research_text
from app.services.originality.similarity_engine import find_similar_chunks
from app.services.originality.text_chunker import create_chunks


# ============================================================
# CONFIGURATION
# ============================================================

OPENALEX_URL = "https://api.openalex.org/works"

SEMANTIC_SCHOLAR_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)

CROSSREF_URL = "https://api.crossref.org/works"

MAX_EXTERNAL_CANDIDATES = 12
MAX_EXTERNAL_PDF_DOWNLOADS = 8

HTTP_TIMEOUT = 20.0


# ============================================================
# TEXT HELPERS
# ============================================================

def _norm_title(value: str) -> str:
    """
    Normalize paper title for deduplication.
    """

    value = re.sub(
        r"[^a-z0-9\s]",
        " ",
        (value or "").lower(),
    )

    return re.sub(r"\s+", " ", value).strip()


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF stored in memory.
    """

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))

        pages = []

        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue

        return "\n".join(pages)

    except Exception as exc:
        raise ValueError(
            f"Unable to read manuscript PDF: {exc}"
        ) from exc


def _query_from_text(text: str) -> str:
    """
    Create a short scholarly search query from manuscript text.

    We use the beginning of the cleaned manuscript because it commonly
    contains title, abstract, introduction and research-topic information.
    """

    cleaned = re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()

    if not cleaned:
        return ""

    return cleaned[:900]


# ============================================================
# OPENALEX
# ============================================================

def _openalex_candidates(query: str) -> List[Dict]:
    """
    Search OpenAlex for candidate papers.
    """

    if not query:
        return []

    params = {
        "search": query,
        "per-page": 8,
        "select": (
            "id,"
            "display_name,"
            "doi,"
            "publication_year,"
            "authorships,"
            "open_access,"
            "best_oa_location,"
            "primary_location"
        ),
    }

    try:
        response = httpx.get(
            OPENALEX_URL,
            params=params,
            timeout=HTTP_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except Exception:
        return []

    results = []

    for item in data.get("results", []):

        title = item.get("display_name") or ""

        open_access = item.get("open_access") or {}

        best_location = item.get(
            "best_oa_location"
        ) or {}

        primary_location = item.get(
            "primary_location"
        ) or {}

        pdf_url = (
            best_location.get("pdf_url")
            or primary_location.get("pdf_url")
        )

        landing_url = (
            best_location.get("landing_page_url")
            or primary_location.get("landing_page_url")
        )

        authors = []

        for author in item.get("authorships") or []:

            author_data = author.get("author") or {}

            name = author_data.get(
                "display_name"
            )

            if name:
                authors.append(name)

        results.append(
            {
                "provider": "OpenAlex",
                "provider_id": item.get("id"),
                "title": title,
                "doi": item.get("doi"),
                "year": item.get("publication_year"),
                "authors": authors,
                "url": landing_url or item.get("doi"),
                "pdf_url": pdf_url,
                "open_access": bool(
                    open_access.get("is_oa")
                ),
            }
        )

    return results


# ============================================================
# SEMANTIC SCHOLAR
# ============================================================

def _semantic_scholar_candidates(
    query: str,
) -> List[Dict]:
    """
    Search Semantic Scholar for candidate papers.
    """

    if not query:
        return []

    params = {
        "query": query,
        "limit": 8,
        "fields": (
            "paperId,"
            "title,"
            "authors,"
            "year,"
            "externalIds,"
            "url,"
            "openAccessPdf"
        ),
    }

    try:

        response = httpx.get(
            SEMANTIC_SCHOLAR_URL,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": "ResearchMate-AI/1.0"
            },
        )

        response.raise_for_status()

        data = response.json()

    except Exception:
        return []

    results = []

    for item in data.get("data") or []:

        external_ids = (
            item.get("externalIds")
            or {}
        )

        open_access_pdf = (
            item.get("openAccessPdf")
            or {}
        )

        doi = None

        if external_ids.get("DOI"):
            doi = (
                "https://doi.org/"
                + external_ids["DOI"]
            )

        authors = []

        for author in item.get("authors") or []:

            name = author.get("name")

            if name:
                authors.append(name)

        results.append(
            {
                "provider": "Semantic Scholar",
                "provider_id": item.get("paperId"),
                "title": item.get("title") or "",
                "doi": doi,
                "year": item.get("year"),
                "authors": authors,
                "url": item.get("url"),
                "pdf_url": open_access_pdf.get("url"),
                "open_access": bool(
                    open_access_pdf.get("url")
                ),
            }
        )

    return results


# ============================================================
# CROSSREF
# ============================================================

def _crossref_candidates(
    query: str,
) -> List[Dict]:
    """
    Search Crossref for candidate papers.

    Crossref is mainly used for bibliographic discovery.
    It usually does not provide a directly downloadable PDF.
    """

    if not query:
        return []

    params = {
        "query.bibliographic": query,
        "rows": 8,
        "select": (
            "DOI,"
            "title,"
            "author,"
            "published,"
            "URL"
        ),
    }

    try:

        response = httpx.get(
            CROSSREF_URL,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": (
                    "ResearchMate-AI/1.0 "
                    "(mailto:researchmate@example.com)"
                )
            },
        )

        response.raise_for_status()

        data = response.json()

    except Exception:
        return []

    results = []

    items = (
        data.get("message") or {}
    ).get("items") or []

    for item in items:

        title_list = item.get(
            "title"
        ) or []

        title = (
            title_list[0]
            if title_list
            else ""
        )

        authors = []

        for author in (
            item.get("author") or []
        ):

            given = (
                author.get("given")
                or ""
            )

            family = (
                author.get("family")
                or ""
            )

            name = f"{given} {family}".strip()

            if name:
                authors.append(name)

        published = (
            item.get("published")
            or {}
        )

        date_parts = (
            published.get("date-parts")
            or [[None]]
        )

        year = date_parts[0][0]

        doi = None

        if item.get("DOI"):
            doi = (
                "https://doi.org/"
                + item["DOI"]
            )

        results.append(
            {
                "provider": "Crossref",
                "provider_id": item.get("DOI"),
                "title": title,
                "doi": doi,
                "year": year,
                "authors": authors,
                "url": item.get("URL"),
                "pdf_url": None,
                "open_access": False,
            }
        )

    return results


# ============================================================
# EXTERNAL SOURCE DISCOVERY
# ============================================================

def discover_external_sources(
    query: str,
) -> List[Dict]:
    """
    Discover candidate papers from:

    - OpenAlex
    - Semantic Scholar
    - Crossref

    Metadata is collected first.

    Only sources with accessible PDF/full text are used
    for actual textual similarity.
    """

    candidates = []

    candidates.extend(
        _openalex_candidates(query)
    )

    candidates.extend(
        _semantic_scholar_candidates(query)
    )

    candidates.extend(
        _crossref_candidates(query)
    )

    deduped: Dict[str, Dict] = {}

    for item in candidates:

        title_key = _norm_title(
            item.get("title")
        )

        doi_key = (
            item.get("doi")
            or ""
        ).lower().strip()

        key = (
            doi_key
            or title_key
        )

        if not key:
            continue

        existing = deduped.get(key)

        if existing is None:

            deduped[key] = item

        else:

            # Prefer source that exposes PDF.
            if (
                not existing.get("pdf_url")
                and item.get("pdf_url")
            ):
                deduped[key] = item

    return list(
        deduped.values()
    )[:MAX_EXTERNAL_CANDIDATES]


# ============================================================
# PDF DOWNLOAD
# ============================================================

def _download_pdf(
    pdf_url: Optional[str],
) -> Optional[bytes]:
    """
    Download an accessible PDF.

    Returns None if the URL is not accessible or is not a PDF.
    """

    if not pdf_url:
        return None

    try:

        response = httpx.get(
            pdf_url,
            timeout=HTTP_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "ResearchMate-AI/1.0"
            },
        )

        response.raise_for_status()

        content_type = (
            response.headers.get(
                "content-type"
            )
            or ""
        ).lower()

        content = response.content

        # Check both MIME type and PDF magic bytes.
        if (
            "pdf" in content_type
            or content[:4] == b"%PDF"
        ):
            return content

    except Exception:
        return None

    return None


# ============================================================
# MAIN UPLOADED MANUSCRIPT ANALYSIS
# ============================================================

def analyze_uploaded_manuscript(
    db: Session,
    project_id: int,
    pdf_bytes: bytes,
    filename: str,
    *,
    include_saved_project_papers: bool = True,
) -> Dict:
    """
    Analyze a manuscript uploaded by the user.

    IMPORTANT:

    The uploaded manuscript is NOT inserted into
    LiteraturePaper.

    It is processed temporarily in memory.

    Comparison sources:

    1. Saved project papers
    2. OpenAlex
    3. Semantic Scholar
    4. Crossref
    5. Accessible external PDFs

    The existing lexical similarity engine is reused.
    """

    # ========================================================
    # 1. EXTRACT USER MANUSCRIPT
    # ========================================================

    raw_text = _extract_pdf_text(
        pdf_bytes
    )

    if not raw_text.strip():
        raise ValueError(
            "No text could be extracted from the uploaded PDF."
        )

    # ========================================================
    # 2. CLEAN MANUSCRIPT
    # ========================================================

    cleaned_target = clean_research_text(
        raw_text
    )

    # ========================================================
    # 3. CREATE TARGET CHUNKS
    # ========================================================

    target_chunks = create_chunks(
        cleaned_target,
        min_words=20,
        max_words=120,
    )

    if not target_chunks:

        raise ValueError(
            "No usable research text was found in the manuscript."
        )

    # ========================================================
    # STORAGE
    # ========================================================

    all_matches: List[Dict] = []

    source_results: List[Dict] = []

    # ========================================================
    # 4. SAVED PROJECT PAPERS
    # ========================================================

    if include_saved_project_papers:

        saved_papers = (
            db.query(
                LiteraturePaper
            )
            .filter(
                LiteraturePaper.project_id
                == project_id
            )
            .order_by(
                LiteraturePaper.id.asc()
            )
            .all()
        )

        for paper in saved_papers:

            analysis = (
                db.query(
                    PaperAnalysis
                )
                .filter(
                    PaperAnalysis.literature_paper_id
                    == paper.id,

                    PaperAnalysis.project_id
                    == project_id,
                )
                .order_by(
                    PaperAnalysis.id.desc()
                )
                .first()
            )

            # No extracted text → cannot compare.
            if (
                not analysis
                or not (
                    analysis.extracted_text
                    or ""
                ).strip()
            ):
                continue

            cleaned_source = (
                clean_research_text(
                    analysis.extracted_text
                )
            )

            source_chunks = create_chunks(
                cleaned_source,
                min_words=20,
                max_words=120,
            )

            if not source_chunks:
                continue

            # ------------------------------------------------
            # Compare user manuscript with this saved paper.
            # ------------------------------------------------

            matches = find_similar_chunks(
                target_chunks,
                source_chunks,
                similarity_threshold=35.0,
            )

            # ------------------------------------------------
            # Attach exact source metadata.
            # ------------------------------------------------

            for match in matches:

                all_matches.append(
                    {
                        **match,

                        "source_type":
                            "saved_project_paper",

                        "source_paper_id":
                            paper.id,

                        "source_title":
                            paper.title,

                        "source_url":
                            paper.url,

                        "source_doi":
                            paper.doi,
                    }
                )

            source_results.append(
                {
                    "source_type":
                        "saved_project_paper",

                    "source_paper_id":
                        paper.id,

                    "source_title":
                        paper.title,

                    "source_url":
                        paper.url,

                    "source_doi":
                        paper.doi,

                    "source_chunks":
                        len(source_chunks),

                    "total_matches":
                        len(matches),
                }
            )

    # ========================================================
    # 5. BUILD EXTERNAL SEARCH QUERY
    # ========================================================

    query = _query_from_text(
        cleaned_target
    )

    # ========================================================
    # 6. DISCOVER EXTERNAL PAPERS
    # ========================================================

    external_candidates = (
        discover_external_sources(
            query
        )
    )

    accessible_external = 0

    metadata_only_external = 0

    # ========================================================
    # 7. DOWNLOAD ACCESSIBLE EXTERNAL PAPERS
    # ========================================================

    for candidate in external_candidates:

        # Limit expensive PDF downloads.
        if (
            accessible_external
            >= MAX_EXTERNAL_PDF_DOWNLOADS
        ):

            metadata_only_external += 1

            continue

        pdf_bytes_external = (
            _download_pdf(
                candidate.get("pdf_url")
            )
        )

        # ----------------------------------------------------
        # PDF unavailable
        # ----------------------------------------------------

        if not pdf_bytes_external:

            metadata_only_external += 1

            source_results.append(
                {
                    "source_type":
                        "external_metadata_only",

                    "provider":
                        candidate.get(
                            "provider"
                        ),

                    "provider_id":
                        candidate.get(
                            "provider_id"
                        ),

                    "title":
                        candidate.get(
                            "title"
                        ),

                    "doi":
                        candidate.get(
                            "doi"
                        ),

                    "year":
                        candidate.get(
                            "year"
                        ),

                    "authors":
                        candidate.get(
                            "authors"
                        ),

                    "url":
                        candidate.get(
                            "url"
                        ),

                    "pdf_url":
                        candidate.get(
                            "pdf_url"
                        ),

                    "open_access":
                        candidate.get(
                            "open_access"
                        ),
                }
            )

            continue

        # ====================================================
        # 8. EXTRACT EXTERNAL PDF TEXT
        # ====================================================

        external_text = (
            _extract_pdf_text(
                pdf_bytes_external
            )
        )

        cleaned_external = (
            clean_research_text(
                external_text
            )
        )

        external_chunks = create_chunks(
            cleaned_external,
            min_words=20,
            max_words=120,
        )

        if not external_chunks:

            metadata_only_external += 1

            continue

        accessible_external += 1

        # ====================================================
        # 9. COMPARE USER PAPER WITH EXTERNAL PAPER
        # ====================================================

        matches = find_similar_chunks(
            target_chunks,
            external_chunks,
            similarity_threshold=35.0,
        )

        # ====================================================
        # 10. ATTACH EXTERNAL SOURCE METADATA
        # ====================================================

        for match in matches:

            all_matches.append(
                {
                    **match,

                    "source_type":
                        "external",

                    "source_provider":
                        candidate.get(
                            "provider"
                        ),

                    "source_provider_id":
                        candidate.get(
                            "provider_id"
                        ),

                    "source_title":
                        candidate.get(
                            "title"
                        ),

                    "source_url":
                        candidate.get(
                            "url"
                        ),

                    "source_doi":
                        candidate.get(
                            "doi"
                        ),

                    "source_year":
                        candidate.get(
                            "year"
                        ),

                    "source_authors":
                        candidate.get(
                            "authors"
                        ),
                }
            )

        # ====================================================
        # 11. STORE EXTERNAL SOURCE INFO
        # ====================================================

        source_results.append(
            {
                "source_type":
                    "external_full_text",

                "source_provider":
                    candidate.get(
                        "provider"
                    ),

                "source_provider_id":
                    candidate.get(
                        "provider_id"
                    ),

                "source_title":
                    candidate.get(
                        "title"
                    ),

                "source_url":
                    candidate.get(
                        "url"
                    ),

                "source_doi":
                    candidate.get(
                        "doi"
                    ),

                "source_year":
                    candidate.get(
                        "year"
                    ),

                "source_authors":
                    candidate.get(
                        "authors"
                    ),

                "source_chunks":
                    len(external_chunks),

                "total_matches":
                    len(matches),
            }
        )

    # ========================================================
    # 12. DEDUPLICATE TARGET CHUNK MATCHES
    # ========================================================

    best_match_by_target: Dict[
        int,
        Dict
    ] = {}

    for match in all_matches:

        chunk_id = match.get(
            "paper_chunk_id"
        )

        if chunk_id is None:
            continue

        old = best_match_by_target.get(
            chunk_id
        )

        if (
            old is None
            or match.get(
                "similarity_score",
                0
            )
            > old.get(
                "similarity_score",
                0
            )
        ):

            best_match_by_target[
                chunk_id
            ] = match

    unique_matches = list(
        best_match_by_target.values()
    )

    # Strongest matches first.
    unique_matches.sort(
        key=lambda item: item.get(
            "similarity_score",
            0
        ),
        reverse=True,
    )

    # ========================================================
    # 13. CALCULATE SIMILARITY STATISTICS
    # ========================================================

    total_target_chunks = len(
        target_chunks
    )

    matched_target_chunks = len(
        unique_matches
    )

    exact_chunks = {
        match["paper_chunk_id"]

        for match in unique_matches

        if match.get(
            "match_type"
        ) == "exact"
    }

    similar_chunks = {
        match["paper_chunk_id"]

        for match in unique_matches

        if match.get(
            "match_type"
        ) == "similar"
    }

    # ========================================================
    # OVERALL SIMILARITY
    # ========================================================

    overall_similarity = (

        matched_target_chunks
        / total_target_chunks
        * 100

        if total_target_chunks

        else 0.0
    )

    # ========================================================
    # EXACT SIMILARITY
    # ========================================================

    exact_similarity = (

        len(exact_chunks)
        / total_target_chunks
        * 100

        if total_target_chunks

        else 0.0
    )

    # ========================================================
    # LEXICAL SIMILARITY
    # ========================================================

    lexical_similarity = (

        len(similar_chunks)
        / total_target_chunks
        * 100

        if total_target_chunks

        else 0.0
    )

    # ========================================================
    # 14. RISK LEVEL
    # ========================================================

    if overall_similarity >= 30:

        risk_level = "high"

    elif overall_similarity >= 15:

        risk_level = "medium"

    elif overall_similarity >= 5:

        risk_level = "low"

    else:

        risk_level = "minimal"

    # ========================================================
    # 15. FINAL RESPONSE
    # ========================================================

    return {

        # ----------------------------------------------------
        # Manuscript information
        # ----------------------------------------------------

        "project_id":
            project_id,

        "input_type":
            "uploaded_manuscript",

        "filename":
            filename,

        # ----------------------------------------------------
        # Source counts
        # ----------------------------------------------------

        "saved_project_sources_checked":
            sum(
                1

                for source
                in source_results

                if source.get(
                    "source_type"
                )
                == "saved_project_paper"
            ),

        "external_candidates_found":
            len(
                external_candidates
            ),

        "external_full_text_sources":
            accessible_external,

        "external_metadata_only_sources":
            metadata_only_external,

        # ----------------------------------------------------
        # Target chunks
        # ----------------------------------------------------

        "target_chunks":
            total_target_chunks,

        # ----------------------------------------------------
        # Similarity
        # ----------------------------------------------------

        "overall_similarity":
            round(
                overall_similarity,
                2,
            ),

        "exact_similarity":
            round(
                exact_similarity,
                2,
            ),

        "lexical_similarity":
            round(
                lexical_similarity,
                2,
            ),

        # ----------------------------------------------------
        # Semantic similarity
        #
        # Embeddings are not implemented yet.
        # ----------------------------------------------------

        "semantic_similarity":
            0.0,

        # ----------------------------------------------------
        # Matches
        # ----------------------------------------------------

        "total_matches":
            len(
                unique_matches
            ),

        "risk_level":
            risk_level,

        "matches":
            unique_matches,

        # ----------------------------------------------------
        # Sources
        # ----------------------------------------------------

        "sources":
            source_results,

        # ----------------------------------------------------
        # Limitations
        # ----------------------------------------------------

        "limitations":
            [

                (
                    "This is a textual "
                    "similarity/originality "
                    "risk check, not a "
                    "plagiarism verdict."
                ),

                (
                    "External similarity "
                    "is checked only against "
                    "discovered sources for "
                    "which accessible full "
                    "text was available."
                ),

                (
                    "Metadata-only sources "
                    "are reported but are "
                    "not used to calculate "
                    "textual similarity."
                ),

                (
                    "Semantic embedding "
                    "similarity is not "
                    "implemented yet; "
                    "semantic_similarity "
                    "is therefore 0.0."
                ),

            ],
    }