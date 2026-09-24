import re
from typing import List, Dict


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_into_paragraphs(text: str) -> List[str]:
    if not text:
        return []

    paragraphs = re.split(r"\n\s*\n", text)

    return [
        paragraph.strip()
        for paragraph in paragraphs
        if paragraph.strip()
    ]


def split_into_sentences(text: str) -> List[str]:
    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?])\s+(?=[A-Z0-9])",
        text,
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def create_chunks(
    text: str,
    min_words: int = 20,
    max_words: int = 120,
) -> List[Dict]:

    cleaned_text = clean_text(text)
    paragraphs = split_into_paragraphs(cleaned_text)

    chunks = []
    chunk_id = 1

    for paragraph_index, paragraph in enumerate(
        paragraphs,
        start=1,
    ):

        sentences = split_into_sentences(paragraph)
        current_chunk = []

        for sentence in sentences:

            current_chunk.append(sentence)

            current_text = " ".join(current_chunk)
            word_count = len(current_text.split())

            if word_count >= min_words:

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "paragraph_index": paragraph_index,
                        "text": current_text,
                        "word_count": word_count,
                    }
                )

                chunk_id += 1
                current_chunk = []

        if current_chunk:

            remaining_text = " ".join(current_chunk)
            word_count = len(remaining_text.split())

            if word_count >= min_words:

                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "paragraph_index": paragraph_index,
                        "text": remaining_text,
                        "word_count": word_count,
                    }
                )

                chunk_id += 1

    return chunks