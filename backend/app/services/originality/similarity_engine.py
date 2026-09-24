from typing import Dict, List, Set
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normalize extracted PDF text before similarity comparison.

    Keeps words, numbers and useful technical punctuation while removing
    PDF noise and repeated whitespace.
    """
    if not text:
        return ""

    text = str(text).lower()

    # Common PDF dash variants
    text = re.sub(r"[–—−]", "-", text)

    # Keep alphanumeric text and a small set of useful symbols.
    text = re.sub(r"[^a-z0-9\s._%+-]", " ", text)

    # Collapse whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# EXACT WORD SIMILARITY
# ============================================================

def _word_tokens(text: str) -> List[str]:
    return re.findall(
        r"[a-zA-Z0-9][a-zA-Z0-9._%+-]*",
        normalize_text(text),
    )


def calculate_exact_similarity(
    text_a: str,
    text_b: str,
) -> float:
    """
    Measure shared-word overlap.

    This is intentionally conservative:
    exact_similarity is high only when a large portion of the shorter
    text is made up of the same words.
    """
    a = _word_tokens(text_a)
    b = _word_tokens(text_b)

    if not a or not b:
        return 0.0

    a_set = set(a)
    b_set = set(b)

    common = len(a_set & b_set)
    denominator = min(len(a_set), len(b_set))

    if denominator == 0:
        return 0.0

    return (common / denominator) * 100.0


# ============================================================
# MEANINGFUL CONTENT WORDS
# ============================================================

_SIM_STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "with",
    "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "they", "their", "them", "we", "our",
    "from", "by", "on", "as", "at", "into", "than", "also", "used",
    "using", "use", "can", "may", "will", "would", "could", "should",
    "has", "have", "had", "which", "such", "more", "less", "very",
    "other", "one", "two", "three", "study", "paper", "method",
    "system", "model", "data", "results", "approach",
}


def _meaningful_tokens(text: str) -> Set[str]:
    words = re.findall(
        r"[a-zA-Z][a-zA-Z0-9_-]{2,}",
        normalize_text(text),
    )

    return {
        word
        for word in words
        if word not in _SIM_STOPWORDS
        and not word.isdigit()
    }


def _content_overlap_score(
    text_a: str,
    text_b: str,
) -> float:
    """
    Jaccard overlap over meaningful content words.

    Generic academic words such as 'method', 'system', 'model',
    'study' and 'approach' are removed so they cannot create
    false similarity matches by themselves.
    """
    a = _meaningful_tokens(text_a)
    b = _meaningful_tokens(text_b)

    if not a or not b:
        return 0.0

    intersection = len(a & b)
    union = len(a | b)

    if union == 0:
        return 0.0

    return (intersection / union) * 100.0


def _meaningful_overlap_count(
    text_a: str,
    text_b: str,
) -> int:
    return len(
        _meaningful_tokens(text_a)
        & _meaningful_tokens(text_b)
    )


# ============================================================
# STRUCTURAL TEXT FILTER
# ============================================================

def _is_structural_text(text: str) -> bool:
    """
    Paper-organization sentences are not useful plagiarism evidence.
    """
    s = text.lower().strip()

    patterns = [
        r"^the (remainder|rest) of (the )?paper",
        r"^the paper is structured",
        r"^this paper is organized",
        r"^the remainder of",
        r"^in section \d",
        r"^section \d",
        r"^the rest of the paper",
    ]

    return any(
        re.search(pattern, s, re.I)
        for pattern in patterns
    )


# ============================================================
# SIMILARITY ENGINE
# ============================================================

def find_similar_chunks(
    paper_chunks: List[Dict],
    source_chunks: List[Dict],
    similarity_threshold: float = 35.0,
) -> List[Dict]:
    """
    Compare target-paper chunks against source-paper chunks.

    Three signals are calculated:

    1. exact word overlap
    2. TF-IDF cosine similarity
    3. meaningful content-word overlap

    TF-IDF alone is NOT treated as sufficient evidence because
    generic academic language can create false 35-45% matches.

    A match is retained when:
      - exact similarity is strong, OR
      - TF-IDF is strong AND meaningful overlap is strong enough.

    This remains lexical similarity. It is NOT true semantic/embedding
    similarity.
    """

    matches: List[Dict] = []

    if not paper_chunks or not source_chunks:
        return matches

    # --------------------------------------------------------
    # Normalize text
    # --------------------------------------------------------

    paper_texts = [
        normalize_text(chunk["text"])
        for chunk in paper_chunks
    ]

    source_texts = [
        normalize_text(chunk["text"])
        for chunk in source_chunks
    ]

    # --------------------------------------------------------
    # Fit TF-IDF once over the complete corpus
    # --------------------------------------------------------

    all_texts = paper_texts + source_texts

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
    )

    vectors = vectorizer.fit_transform(all_texts)

    paper_vectors = vectors[:len(paper_texts)]
    source_vectors = vectors[len(paper_texts):]

    # --------------------------------------------------------
    # Complete cosine similarity matrix
    # --------------------------------------------------------

    similarity_matrix = cosine_similarity(
        paper_vectors,
        source_vectors,
    )

    # --------------------------------------------------------
    # Best source match for every target chunk
    # --------------------------------------------------------

    for paper_index, paper_chunk in enumerate(paper_chunks):

        row = similarity_matrix[paper_index]

        best_source_index = int(row.argmax())

        tfidf_score = (
            float(row[best_source_index])
            * 100.0
        )

        source_chunk = source_chunks[best_source_index]

        target_text = paper_chunk["text"]
        source_text = source_chunk["text"]

        # ----------------------------------------------------
        # Ignore paper-organization boilerplate
        # ----------------------------------------------------

        if (
            _is_structural_text(target_text)
            or _is_structural_text(source_text)
        ):
            continue

        # ----------------------------------------------------
        # Exact wording signal
        # ----------------------------------------------------

        exact_score = calculate_exact_similarity(
            target_text,
            source_text,
        )

        # ----------------------------------------------------
        # Meaningful content signal
        # ----------------------------------------------------

        content_overlap = _content_overlap_score(
            target_text,
            source_text,
        )

        overlap_count = _meaningful_overlap_count(
            target_text,
            source_text,
        )

        # ----------------------------------------------------
        # Classification
        # ----------------------------------------------------

        if exact_score >= 70:

            final_score = exact_score
            match_type = "exact"

        elif (
            tfidf_score >= 45
            and content_overlap >= 18
            and overlap_count >= 4
        ):

            final_score = max(
                tfidf_score,
                content_overlap,
            )
            match_type = "similar"

        elif (
            tfidf_score >= 35
            and content_overlap >= 25
            and overlap_count >= 5
        ):

            final_score = max(
                tfidf_score,
                content_overlap,
            )
            match_type = "similar"

        else:
            # Weak lexical similarity is ignored.
            continue

        if final_score < similarity_threshold:
            continue

        matches.append(
            {
                "paper_chunk_id": paper_chunk["chunk_id"],
                "source_chunk_id": source_chunk["chunk_id"],
                "matched_text": target_text,
                "source_text": source_text,
                "similarity_score": round(
                    final_score,
                    2,
                ),
                "match_type": match_type,
                "exact_similarity": round(
                    exact_score,
                    2,
                ),
                "tfidf_similarity": round(
                    tfidf_score,
                    2,
                ),
                "content_overlap": round(
                    content_overlap,
                    2,
                ),
                "meaningful_overlap_words": overlap_count,
            }
        )

    # Highest similarity first.
    matches.sort(
        key=lambda item: item["similarity_score"],
        reverse=True,
    )

    return matches


__all__ = [
    "normalize_text",
    "calculate_exact_similarity",
    "find_similar_chunks",
]
