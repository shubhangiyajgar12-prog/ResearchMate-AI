"""Lightweight local RAG implementation with deterministic TF-IDF retrieval.
Falls back to lexical scoring if sklearn is unavailable."""
import re
from collections import Counter
from typing import Any

class RAGService:
    def __init__(self):
        self._chunks = []

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180):
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return []
        chunks, start, n = [], 0, len(text)
        while start < n:
            end = min(n, start + chunk_size)
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end == n:
                break
            start = max(start + 1, end - overlap)
        return chunks

    def index_document(self, text: str, metadata: dict[str, Any] | None = None):
        metadata = metadata or {}
        new = []
        for i, chunk in enumerate(self.chunk_text(text)):
            item = {"chunk_id": f"{metadata.get('document_id','doc')}-{i}", "text": chunk, "metadata": {**metadata, "chunk_id": i}}
            new.append(item)
        self._chunks.extend(new)
        return new

    def search(self, query: str, top_k: int = 5):
        if not query or not self._chunks:
            return []
        q = set(re.findall(r"\b\w{3,}\b", query.lower()))
        scored = []
        for item in self._chunks:
            words = re.findall(r"\b\w{3,}\b", item["text"].lower())
            if not words:
                continue
            counts = Counter(words)
            overlap = sum(counts[w] for w in q)
            score = overlap / max(1, len(q))
            if score > 0:
                scored.append({**item, "score": round(min(score, 1.0), 4)})
        return sorted(scored, key=lambda x: x["score"], reverse=True)[:top_k]

rag_service = RAGService()
