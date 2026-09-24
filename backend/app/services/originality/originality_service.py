from typing import Dict, List
import hashlib
import re

from sqlalchemy.orm import Session

from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis

from app.services.originality.text_chunker import create_chunks
from app.services.originality.similarity_engine import find_similar_chunks
from app.services.originality.citation_service import clean_research_text


def _document_fingerprint(text: str) -> str:
    """
    Create a stable fingerprint from cleaned research text.

    This is used only to detect duplicate/self documents before
    similarity comparison. It is NOT a similarity score.
    """
    normalized = re.sub(r"\s+", " ", text or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9\s.%\-+/]", "", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def analyze_project_paper(
    db: Session,
    project_id: int,
    paper_id: int,
) -> Dict:

    # ---------------------------------------------------------
    # 1. Get target paper
    # ---------------------------------------------------------

    target_paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id,
        )
        .first()
    )

    if not target_paper:
        raise ValueError("Target paper not found for this project.")

    # ---------------------------------------------------------
    # 2. Get target paper PDF analysis
    # ---------------------------------------------------------

    target_analysis = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.literature_paper_id == paper_id,
            PaperAnalysis.project_id == project_id,
        )
        .order_by(PaperAnalysis.id.desc())
        .first()
    )

    if not target_analysis:
        raise ValueError(
            "PDF analysis not found for target paper. "
            "Analyze the PDF before running originality analysis."
        )

    target_text = target_analysis.extracted_text or ""

    if not target_text.strip():
        raise ValueError(
            "Target paper does not contain extracted text."
        )

    # ---------------------------------------------------------
    # 3. Clean target research text
    # ---------------------------------------------------------
    # Removes:
    # - References / bibliography
    # - DOI / URLs
    # - metadata
    # - figure/table captions
    # - university/department information
    # - other non-research text
    #
    # This prevents common reference entries and metadata from
    # artificially increasing similarity.
    # ---------------------------------------------------------

    cleaned_target_text = clean_research_text(target_text)

    if not cleaned_target_text.strip():
        raise ValueError(
            "No usable research text remains after cleaning target paper."
        )

    # Fingerprint the cleaned manuscript once. Any saved source with
    # the same cleaned-text fingerprint is the same/duplicate document
    # and must NOT contribute to originality similarity.
    target_fingerprint = _document_fingerprint(cleaned_target_text)

    # ---------------------------------------------------------
    # 4. Create target chunks
    # ---------------------------------------------------------

    target_chunks = create_chunks(
        cleaned_target_text,
        min_words=20,
        max_words=120,
    )

    if not target_chunks:
        raise ValueError(
            "Unable to create text chunks from target paper."
        )

    # ---------------------------------------------------------
    # 5. Get comparison papers
    # ---------------------------------------------------------

    source_papers = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id,
            LiteraturePaper.id != paper_id,
        )
        .order_by(LiteraturePaper.id.asc())
        .all()
    )

    source_results: List[Dict] = []
    all_matches: List[Dict] = []
    excluded_duplicate_sources: List[Dict] = []

    # ---------------------------------------------------------
    # 6. Compare target paper against each source paper
    # ---------------------------------------------------------

    for source_paper in source_papers:

        source_analysis = (
            db.query(PaperAnalysis)
            .filter(
                PaperAnalysis.literature_paper_id == source_paper.id,
                PaperAnalysis.project_id == project_id,
            )
            .order_by(PaperAnalysis.id.desc())
            .first()
        )

        # Skip papers for which no PDF analysis/full text exists.
        if not source_analysis:
            continue

        source_text = source_analysis.extracted_text or ""

        if not source_text.strip():
            continue

        # -----------------------------------------------------
        # Clean source research text
        # -----------------------------------------------------

        cleaned_source_text = clean_research_text(source_text)

        if not cleaned_source_text.strip():
            continue

        # -----------------------------------------------------
        # IMPORTANT: Exclude exact duplicate/self documents.
        #
        # Uploaded manuscripts may not have the same database paper_id
        # as an already-saved copy of the same paper. Therefore the
        # existing "id != paper_id" filter is not sufficient.
        #
        # We compare cleaned-text fingerprints so the same manuscript
        # cannot inflate its own similarity score.
        # -----------------------------------------------------
        source_fingerprint = _document_fingerprint(cleaned_source_text)

        if source_fingerprint == target_fingerprint:
            excluded_duplicate_sources.append(
                {
                    "source_paper_id": source_paper.id,
                    "source_title": source_paper.title,
                    "source_url": source_paper.url,
                    "source_doi": source_paper.doi,
                    "reason": "duplicate_of_target_document",
                }
            )
            continue

        # -----------------------------------------------------
        # Create source chunks
        # -----------------------------------------------------

        source_chunks = create_chunks(
            cleaned_source_text,
            min_words=20,
            max_words=120,
        )

        if not source_chunks:
            continue

        # -----------------------------------------------------
        # Similarity comparison
        # -----------------------------------------------------

        matches = find_similar_chunks(
            target_chunks,
            source_chunks,
            similarity_threshold=35.0,
        )

        # -----------------------------------------------------
        # Add source information to every match
        # -----------------------------------------------------

        enriched_matches = []

        for match in matches:

            enriched_match = {
                **match,

                "source_paper_id": source_paper.id,

                "source_title": source_paper.title,

                "source_url": source_paper.url,

                "source_doi": source_paper.doi,
            }

            enriched_matches.append(enriched_match)
            all_matches.append(enriched_match)

        # -----------------------------------------------------
        # Source-level statistics
        # -----------------------------------------------------

        unique_target_chunks = {
            match["paper_chunk_id"]
            for match in enriched_matches
        }

        exact_target_chunks = {
            match["paper_chunk_id"]
            for match in enriched_matches
            if match["match_type"] == "exact"
        }

        similar_target_chunks = {
            match["paper_chunk_id"]
            for match in enriched_matches
            if match["match_type"] == "similar"
        }

        source_results.append(
            {
                "source_paper_id": source_paper.id,
                "source_title": source_paper.title,
                "source_url": source_paper.url,
                "source_doi": source_paper.doi,

                "source_chunks": len(source_chunks),

                "total_matches": len(enriched_matches),

                "matched_target_chunks": len(
                    unique_target_chunks
                ),

                "exact_matches": len(
                    exact_target_chunks
                ),

                "similar_matches": len(
                    similar_target_chunks
                ),
            }
        )

    # ---------------------------------------------------------
    # 7. Remove duplicate target-chunk matches
    # ---------------------------------------------------------
    # A single target chunk can match multiple source papers.
    # For overall similarity we count the target chunk only once.
    # The strongest match is retained.
    # ---------------------------------------------------------

    best_match_by_target_chunk: Dict[int, Dict] = {}

    for match in all_matches:

        chunk_id = match["paper_chunk_id"]

        existing = best_match_by_target_chunk.get(chunk_id)

        if (
            existing is None
            or match["similarity_score"]
            > existing["similarity_score"]
        ):
            best_match_by_target_chunk[chunk_id] = match

    unique_matches = list(
        best_match_by_target_chunk.values()
    )

    # ---------------------------------------------------------
    # 8. Sort matches
    # ---------------------------------------------------------

    unique_matches.sort(
        key=lambda item: item["similarity_score"],
        reverse=True,
    )

    # ---------------------------------------------------------
    # 9. Calculate similarity statistics
    # ---------------------------------------------------------

    total_target_chunks = len(target_chunks)

    matched_target_chunks = len(unique_matches)

    exact_target_chunks = len(
        {
            match["paper_chunk_id"]
            for match in unique_matches
            if match["match_type"] == "exact"
        }
    )

    similar_target_chunks = len(
        {
            match["paper_chunk_id"]
            for match in unique_matches
            if match["match_type"] == "similar"
        }
    )

    # ---------------------------------------------------------
    # Overall similarity
    # ---------------------------------------------------------

    if total_target_chunks > 0:

        overall_similarity = (
            matched_target_chunks
            / total_target_chunks
        ) * 100

        exact_similarity = (
            exact_target_chunks
            / total_target_chunks
        ) * 100

        lexical_similarity = (
            similar_target_chunks
            / total_target_chunks
        ) * 100

    else:

        overall_similarity = 0.0
        exact_similarity = 0.0
        lexical_similarity = 0.0

    # ---------------------------------------------------------
    # 10. Semantic similarity
    # ---------------------------------------------------------
    # True embedding-based semantic similarity is not yet
    # implemented. Therefore we intentionally keep this at 0.0
    # instead of pretending TF-IDF is semantic similarity.
    # ---------------------------------------------------------

    semantic_similarity = 0.0

    # ---------------------------------------------------------
    # 11. Risk classification
    # ---------------------------------------------------------
    #
    # This is a textual similarity risk indicator.
    # It is NOT a plagiarism verdict.
    #
    # Thresholds:
    # >= 30  -> high
    # >= 15  -> medium
    # >= 5   -> low
    # < 5    -> minimal
    # ---------------------------------------------------------

    if overall_similarity >= 30:
        risk_level = "high"

    elif overall_similarity >= 15:
        risk_level = "medium"

    elif overall_similarity >= 5:
        risk_level = "low"

    else:
        risk_level = "minimal"

    # ---------------------------------------------------------
    # 12. Final result
    # ---------------------------------------------------------

    result = {
        "project_id": project_id,

        "paper_id": paper_id,

        "target_title": target_paper.title,

        "target_chunks": total_target_chunks,

        "sources_checked": len(source_results),

        "excluded_duplicate_sources": excluded_duplicate_sources,

        "duplicate_sources_excluded_count": len(
            excluded_duplicate_sources
        ),

        "overall_similarity": round(
            overall_similarity,
            2,
        ),

        "exact_similarity": round(
            exact_similarity,
            2,
        ),

        "semantic_similarity": round(
            semantic_similarity,
            2,
        ),

        "lexical_similarity": round(
            lexical_similarity,
            2,
        ),

        "total_matches": len(unique_matches),

        "risk_level": risk_level,

        "matches": unique_matches,

        "source_results": source_results,
    }

    return result