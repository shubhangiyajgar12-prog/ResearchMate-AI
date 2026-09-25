"""Evidence-first Literature Matrix API.

Extracts only evidence explicitly present in saved title/abstract metadata.
It avoids treating proposals, background statements, or generic dataset phrases
as results/datasets, and never invents research gaps.
"""
import re
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.literature_paper import LiteraturePaper

router = APIRouter(prefix="/literature", tags=["Literature Intelligence"])


class LiteratureMatrixRequest(BaseModel):
    project_id: int
    paper_ids: list[int] = Field(min_length=1)


NOT_REPORTED = "Not reported in saved metadata/abstract"
NOT_EXPLICIT = "Not explicitly reported in saved metadata/abstract"


def clean(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip(" -") for p in parts if len(p.strip(" -")) >= 20]


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        key = re.sub(r"\W+", " ", item.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


METHOD_PATTERNS = [
    ("MTCNN / multitask cascaded CNN", r"multitask cascaded|mtcnn"),
    ("Transformer", r"\btransformer(?:s)?\b"),
    ("BERT", r"\bbert\b"),
    ("GPT", r"\bgpt(?:-\d+(?:\.\d+)?)?\b"),
    ("CNN", r"\bcnn(?:s)?\b|convolutional neural network"),
    ("RNN", r"\brnn(?:s)?\b|recurrent neural network"),
    ("LSTM", r"\blstm(?:s)?\b|long short[- ]term memory"),
    ("GRU", r"\bgru(?:s)?\b|gated recurrent unit"),
    ("YOLO", r"\byolo(?:v\d+(?:\.\d+)?)?\b"),
    ("SVM", r"\bsvm\b|support vector machine"),
    ("Random Forest", r"random forest"),
    ("Decision Tree", r"decision tree"),
    ("XGBoost", r"\bxgboost\b"),
    ("Logistic Regression", r"logistic regression"),
    ("Linear Regression", r"linear regression"),
    ("K-means", r"k[- ]means"),
    ("KNN", r"\bknn\b|k[- ]nearest neighbors"),
    ("Naive Bayes", r"naive bayes"),
    ("U-Net", r"\bu[- ]net\b"),
    ("ResNet", r"\bresnet\b"),
    ("VGG", r"\bvgg(?:-\d+)?\b"),
    ("GAN", r"\bgan(?:s)?\b|generative adversarial network"),
    ("Autoencoder", r"autoencoder"),
    ("Attention", r"attention mechanism|self[- ]attention"),
    ("Deep Learning", r"deep learning"),
    ("Machine Learning", r"machine learning"),
    ("Reinforcement Learning", r"reinforcement learning"),
    ("Graph Neural Network", r"graph neural network|\bgnn\b"),
    ("PCA", r"principal component analysis|\bpca\b"),
    ("TF-IDF", r"tf[- ]idf"),
    ("BM25", r"\bbm25\b"),
]


def extract_methods(text: str) -> list[str]:
    low = text.lower()
    return [label for label, pattern in METHOD_PATTERNS if re.search(pattern, low, re.I)][:8]


def extract_dataset(text: str) -> str:
    raw = clean(text)

    # Only accept a concrete named dataset/corpus/benchmark.  Do not use
    # case-insensitive matching here: otherwise phrases such as "and benchmark"
    # can be captured as if they were dataset names.
    named_patterns = [
        r"\b(?:using|used|evaluated on|tested on|trained on|trained using|based on|from)\s+(?:the\s+)?([A-Z][A-Za-z0-9&._/-]*(?:\s+[A-Z][A-Za-z0-9&._/-]*){0,5})\s+(?:dataset|corpus|benchmark)\b",
        r"\b([A-Z][A-Za-z0-9&._/-]*(?:\s+[A-Z][A-Za-z0-9&._/-]*){0,5})\s+(?:dataset|corpus|benchmark)\b",
    ]
    for pattern in named_patterns:
        for match in re.finditer(pattern, raw):
            value = clean(match.group(1))
            if value and len(value) >= 2 and value.lower() not in {"the", "a", "an"}:
                return value + " dataset"

    # Explicit dataset source/count evidence is acceptable even without a
    # named benchmark.
    count = re.search(r"\b\d[\d,]*\s+(?:patients|samples|images|records|cases|participants|observations)\b", raw, re.I)
    if count:
        return count.group(0)

    source_patterns = [
        r"\b(?:data|records|cases)\s+(?:were|was)\s+(?:obtained|collected|retrieved)\s+from\s+([^.;]+)",
        r"\bdata\s+(?:were|was)\s+collected\s+from\s+([^.;]+)",
    ]
    for pattern in source_patterns:
        match = re.search(pattern, raw, flags=re.I)
        if match:
            value = clean(match.group(1))
            if value:
                return value[:220]
    return NOT_REPORTED

def labelled_sections(text: str) -> dict[str, str]:
    raw = clean(text)
    labels = ["BACKGROUND", "AIMS", "AIM", "OBJECTIVE", "OBJECTIVES", "METHODS", "METHOD", "RESULTS", "CONCLUSIONS", "CONCLUSION"]
    pattern = r"\b(" + "|".join(labels) + r")\s*:\s*"
    matches = list(re.finditer(pattern, raw, flags=re.I))
    sections = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        sections[match.group(1).upper()] = raw[match.end():end].strip()
    return sections


def is_proposal_sentence(s: str) -> bool:
    return bool(re.search(
        r"\b(we\s+(?:propose|present|introduce|develop|design)|this\s+(?:paper|letter|study)\s+(?:proposes|presents|introduces)|proposed\s+(?:method|framework|model|approach))\b",
        s, re.I,
    ))


def extract_problem(text: str, title: str) -> str:
    sections = labelled_sections(text)
    candidates = []
    for key in ("AIMS", "AIM", "OBJECTIVE", "OBJECTIVES", "BACKGROUND"):
        if sections.get(key):
            candidates.extend(sentences(sections[key]))

    ss = sentences(text)
    candidates.extend(ss)
    problem_patterns = [
        r"\b(problem|challenge|need|gap|difficulty|limitation|issue)\b",
        r"\b(remains|remain)\s+(?:challenging|difficult|problematic|limited)",
        r"\b(lack|absence)\s+of\b",
        r"\b(is|are)\s+(?:difficult|challenging)\s+to\b",
    ]
    for s in dedupe(candidates):
        if is_proposal_sentence(s):
            continue
        if any(re.search(p, s, re.I) for p in problem_patterns):
            return s

    # A title is not enough to claim a factual problem; report it only as a task context.
    if title and re.search(r"\b(detection|prediction|classification|alignment|estimation|recognition|forecasting)\b", title, re.I):
        return f"The saved title identifies the study task as: {title}. An explicit research problem statement is not present in the saved abstract."
    return "Research problem not explicitly stated in saved metadata/abstract"


def extract_results(text: str) -> str:
    sections = labelled_sections(text)
    if sections.get("RESULTS"):
        result_sentences = [
            s for s in sentences(sections["RESULTS"])
            if not is_proposal_sentence(s)
            and not re.search(r"\b(?:can|could|may|might|often|frequently|generally)\s+(?:achieve|improve|be used|provide|show)\b", s, re.I)
        ]
        if result_sentences:
            return " ".join(result_sentences[:2])

    ss = sentences(text)
    hits = []
    for s in ss:
        if is_proposal_sentence(s):
            continue
        # Reject generic/background claims such as "recent studies show" or
        # "ML can achieve..." unless a concrete measured outcome is present.
        if re.search(r"\b(?:recent studies|previous studies|prior work|in general|typically|often|frequently)\b", s, re.I):
            continue
        if re.search(r"\b(?:can|could|may|might)\s+(?:achieve|improve|be used|provide|show)\b", s, re.I):
            continue
        has_result_signal = re.search(
            r"\b(results?|findings?|found|demonstrated?|achieved|improved|outperformed|significantly|increased|decreased|estimated|measured|yielded|reduced|accuracy|precision|recall|f1[- ]?score|auc|sensitivity|specificity|incidence|mortality)\b",
            s, re.I,
        )
        has_measure = re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent|cases|patients|samples|times|points)?\b", s, re.I)
        has_past_result = re.search(r"\b(?:found|demonstrated|achieved|improved|outperformed|increased|decreased|estimated|measured|yielded|reduced)\b", s, re.I)
        if has_result_signal and (has_measure or has_past_result):
            hits.append(s)
    return " ".join(dedupe(hits)[:2]) if hits else NOT_REPORTED

def extract_limitations(text: str) -> str:
    sections = labelled_sections(text)
    candidates = []
    for key in ("CONCLUSIONS", "CONCLUSION"):
        if sections.get(key):
            candidates.extend(sentences(sections[key]))
    limitation_patterns = [
        r"\blimitations?\b", r"\blimited\b", r"\black of\b", r"\bsmall sample\b",
        r"\bsmall dataset\b", r"\bchallenge(?:s|d)?\b", r"\bfuture work\b",
        r"\bneeds? further (?:research|investigation|study)\b", r"\bremains? unclear\b",
    ]
    for s in sentences(text):
        if any(re.search(p, s, re.I) for p in limitation_patterns):
            candidates.append(s)
    return " ".join(dedupe(candidates)[:2]) if candidates else NOT_EXPLICIT


def extract_gap(limitation: str) -> str:
    if limitation == NOT_EXPLICIT:
        return "No explicit research gap established from saved abstract"
    return "Potential follow-up area based on the explicitly reported limitation; verify against the full paper and broader recent literature."


def build_matrix(papers: list[LiteraturePaper]) -> dict:
    rows = []
    method_counter = Counter()
    explicit_limitation_rows = []

    for paper in papers:
        abstract = clean(paper.abstract)
        title = clean(paper.title) or "Untitled paper"
        methods = extract_methods(abstract)
        limitation = extract_limitations(abstract)
        for method in methods:
            method_counter[method.lower()] += 1

        row = {
            "paper_id": paper.id,
            "external_paper_id": paper.paper_id,
            "title": title,
            "year": paper.year,
            "research_problem": extract_problem(abstract, title),
            "methodology": ", ".join(methods) if methods else NOT_REPORTED,
            "dataset": extract_dataset(abstract),
            "key_results": extract_results(abstract),
            "limitations": limitation,
            "research_gap": extract_gap(limitation),
            "evidence_basis": "Saved title and abstract metadata",
            "doi": paper.doi,
            "url": paper.url,
        }
        rows.append(row)
        if limitation != NOT_EXPLICIT:
            explicit_limitation_rows.append(row)

    common_methods = [name for name, count in Counter({m: c for m, c in method_counter.items()}).most_common() if count >= 2]
    cross_findings = []
    years = [p.year for p in papers if p.year]
    if years:
        cross_findings.append({"type": "publication_span", "label": "Publication span", "text": f"Selected papers span publication years {min(years)}–{max(years)}."})
    if common_methods:
        cross_findings.append({"type": "shared_methods", "label": "Shared methods", "text": "Methods explicitly mentioned in at least two selected abstracts: " + ", ".join(common_methods) + "."})
    if not cross_findings:
        cross_findings.append({"type": "insufficient_cross_evidence", "label": "Cross-paper evidence", "text": "No repeated methodological pattern could be established from the saved metadata/abstracts."})

    potential_gaps = []
    if len(explicit_limitation_rows) >= 2:
        potential_gaps.append({
            "type": "repeated_limitation",
            "title": "Repeated limitation signals across selected papers",
            "description": "At least two selected abstracts explicitly report limitation/challenge language. This is a follow-up signal, not proof of a research gap or novelty.",
            "affected_paper_ids": [r["paper_id"] for r in explicit_limitation_rows],
            "affected_papers": [r["title"] for r in explicit_limitation_rows],
            "evidence": [r["limitations"] for r in explicit_limitation_rows],
        })

    return {
        "project_id": papers[0].project_id if papers else None,
        "papers": rows,
        "common_methods": common_methods,
        "common_limitations": ["Explicit limitation/challenge language"] if len(explicit_limitation_rows) >= 2 else [],
        "cross_paper_findings": cross_findings,
        "potential_research_gaps": potential_gaps,
        "gap_note": "No explicit cross-paper research gap was established from the selected abstracts." if not potential_gaps else "Potential gap signals are evidence-based follow-up signals, not proof of novelty. Verify full text and broader recent literature.",
        "evidence_note": "Evidence-first deterministic synthesis from saved title/abstract metadata. Background, proposals, and generic dataset phrases are not treated as results or datasets; missing information is reported as unavailable.",
    }


@router.delete("/projects/{project_id}/papers/{paper_id}")
def delete_project_paper(
    project_id: int,
    paper_id: int,
    db: Session = Depends(get_db),
):
    """Remove one saved literature paper from the given project."""

    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.project_id == project_id,
            LiteraturePaper.id == paper_id,
        )
        .first()
    )

    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="Paper not found in this project.",
        )

    db.delete(paper)
    db.commit()

    return {
        "message": "Paper removed from literature library.",
        "paper_id": paper_id,
        "project_id": project_id,
    }


@router.post("/literature-matrix")
def create_literature_matrix(request: LiteratureMatrixRequest, db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(request.paper_ids))
    papers = (
        db.query(LiteraturePaper)
        .filter(LiteraturePaper.project_id == request.project_id, LiteraturePaper.id.in_(ids))
        .order_by(LiteraturePaper.id.asc())
        .all()
    )
    found = {p.id for p in papers}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(status_code=404, detail=f"Selected paper(s) not found in project: {missing}")
    if not papers:
        raise HTTPException(status_code=400, detail="No saved papers were selected.")
    return build_matrix(papers)
