from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import httpx


OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_EMAIL = "researchmate.ai@gmail.com"
CROSSREF_URL = "https://api.crossref.org/works"
CROSSREF_MAILTO = "researchmate.ai@gmail.com"

_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}
CACHE_TTL = timedelta(seconds=90)


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "the", "to", "with",
    "using", "use", "based", "approach", "approaches", "system",
    "study", "studies", "research", "analysis", "development", "design",
    "method", "methods", "model", "models", "framework", "frameworks",
    "paper", "papers", "new", "novel", "proposed", "propose",
    "towards", "toward", "for", "via", "using",
}

# Domain classification is deliberately explicit so common application
# terms such as "rural", "healthcare", "surveillance", etc. are not
# incorrectly collapsed into "General Computer Science".
DOMAIN_RULES = [
    (
        "Healthcare / Medical AI",
        [
            "healthcare", "health care", "medical", "medicine", "clinical",
            "diagnosis", "diagnostic", "disease", "patient", "hospital",
            "radiology", "medical imaging", "electronic health record",
            "ehr", "clinical decision support",
        ],
    ),
    (
        "Traffic Safety / Intelligent Transportation / Computer Vision",
        [
            "helmet", "helmet violation", "motorcycle", "motorcyclist",
            "rider", "traffic", "road safety", "vehicle",
        ],
    ),
    (
        "Security & Surveillance / Computer Vision",
        [
            "weapon", "firearm", "gun detection", "knife detection",
            "surveillance", "cctv", "security camera", "security surveillance",
        ],
    ),
    (
        "Computer Vision / Deep Learning",
        [
            "face", "face detection", "facial", "computer vision",
            "image processing", "object detection", "image classification",
            "image segmentation", "landmark", "yolo", "cnn",
        ],
    ),
    (
        "Cybersecurity",
        [
            "cybersecurity", "cyber security", "intrusion", "malware",
            "phishing", "attack detection", "network security",
        ],
    ),
    (
        "Blockchain / FinTech",
        [
            "blockchain", "smart contract", "defi", "cryptocurrency",
            "financial fraud", "fraud detection", "fintech",
        ],
    ),
    (
        "Natural Language Processing",
        [
            "nlp", "natural language processing", "sentiment",
            "named entity", "machine translation", "text classification",
            "language model", "large language model", "llm",
        ],
    ),
    (
        "Artificial Intelligence / Machine Learning",
        [
            "artificial intelligence", "machine learning", "deep learning",
            "neural network", "ai model",
        ],
    ),
]


TASK_RULES = {
    "diagnosis": [
        "diagnosis",
        "diagnostic",
        "disease diagnosis",
        "clinical diagnosis",
        "medical diagnosis",
        "early diagnosis",
        "risk assessment",
        "clinical decision support",
    ],
    "detection": [
        "detection", "detect", "object detection",
        "face detection", "weapon detection", "helmet detection",
        "localization", "bounding box",
    ],
    "classification": [
        "classification", "classify", "categorization",
    ],
    "prediction": [
        "prediction", "predict", "forecast", "forecasting",
    ],
    "recognition": [
        "recognition", "recognize", "identification", "identify",
    ],
    "segmentation": [
        "segmentation", "segment",
    ],
    "tracking": [
        "tracking", "track",
    ],
}


METHOD_RULES = {
    "Explainable AI": [
        "explainable ai",
        "explainable artificial intelligence",
        "xai",
        "explainability",
        "interpretable ai",
        "interpretable machine learning",
        "interpretability",
    ],
    "YOLO": [
        "yolo", "yolov5", "yolov7", "yolov8",
        "yolov9", "yolov10", "yolov11",
    ],
    "Deep Learning": [
        "deep learning", "cnn",
        "convolutional neural network", "transformer",
    ],
    "Machine Learning": [
        "machine learning", "random forest", "xgboost",
        "svm", "support vector machine",
    ],
    "Transfer Learning": [
        "transfer learning", "fine-tuning", "finetuning",
    ],
    "Computer Vision": [
        "computer vision", "opencv", "image processing",
    ],
    "Faster R-CNN": [
        "faster r-cnn", "faster rcnn",
    ],
    "Multitask Learning": [
        "multitask learning", "multi-task learning",
        "multi task learning",
    ],
    "Federated Learning": [
        "federated learning", "federated",
    ],
}


CONTEXT_RULES = [
    "rural",
    "remote",
    "underserved",
    "low-resource",
    "low resource",
    "community",
    "primary care",
    "real-time",
    "real time",
    "edge",
    "mobile",
    "embedded",
    "nighttime",
    "night time",
    "low-light",
    "low light",
    "adverse weather",
    "urban",
    "surveillance",
    "cctv",
    "unconstrained",
    "outdoor",
    "indoor",
]


# Rural-specific evidence is tracked separately from general healthcare
# evidence so a general healthcare paper is not presented as rural evidence.
RURAL_CONTEXT_TERMS = [
    "rural",
    "rural health",
    "rural healthcare",
    "rural health care",
    "remote",
    "underserved",
    "low-resource",
    "low resource",
    "community health",
    "primary care",
    "rural population",
    "rural populations",
    "rural clinic",
    "rural clinics",
    "rural hospital",
    "rural hospitals",
]


OUTCOME_RULES = [
    "accuracy",
    "precision",
    "recall",
    "f1",
    "f1-score",
    "auc",
    "sensitivity",
    "specificity",
    "mape",
    "rmse",
    "latency",
    "fps",
    "robustness",
    "explainability",
    "interpretability",
    "trust",
    "clinical utility",
    "usability",
    "fairness",
    "privacy",
    "cost",
    "efficiency",
    "performance",
]


# Gap themes are intentionally conservative. They are only emitted after
# explicit limitation/future-work evidence is found in multiple papers.
GAP_PATTERNS = {
    "rural and underserved validation": [
        "rural",
        "remote",
        "underserved",
        "low-resource",
        "low resource",
        "limited resources",
        "rural healthcare",
        "rural health",
    ],
    "explainability and clinical usability": [
        "explainability",
        "interpretability",
        "interpretable",
        "explanation",
        "clinical usability",
        "clinical trust",
        "clinician trust",
    ],
    "generalization across settings": [
        "generalization",
        "generalisation",
        "generalizability",
        "generalizability",
        "domain shift",
        "different settings",
        "different populations",
        "external validation",
        "external dataset",
        "unseen data",
    ],
    "data quality and dataset diversity": [
        "limited dataset",
        "small dataset",
        "dataset size",
        "dataset diversity",
        "data quality",
        "limited data",
        "missing data",
        "imbalanced data",
    ],
    "privacy and deployment constraints": [
        "privacy",
        "data privacy",
        "privacy concerns",
        "deployment",
        "resource-constrained",
        "resource constrained",
        "computational cost",
        "computational resources",
    ],
    "occlusion and viewpoint robustness": [
        "occlusion",
        "viewpoint",
        "view point",
        "pose variation",
        "pose variations",
        "partial visibility",
    ],
}


EXPLICIT_LIMITATION_TERMS = [
    "limitation",
    "limitations",
    "lack of",
    "limited",
    "cannot",
    "can't",
    "unable",
    "not able",
    "remain",
    "remains",
    "still difficult",
    "difficulty",
    "difficult",
    "challenging",
    "challenge",
    "bottleneck",
    "shortcoming",
    "shortcomings",
    "fails to",
    "failure to",
    "underperform",
    "underperforms",
    "underperformed",
    "not generalize",
    "does not generalize",
    "not validated",
    "lack sufficient",
]


FUTURE_WORK_TERMS = [
    "future work",
    "future research",
    "further research",
    "in future",
    "future studies",
    "will investigate",
    "should investigate",
    "should be investigated",
    "remain to be studied",
    "requires further",
    "need further",
    "future direction",
]


POSITIVE_RESULT_TERMS = [
    "achieves",
    "achieved",
    "achieve",
    "demonstrates",
    "demonstrated",
    "demonstrate",
    "outperforms",
    "outperformed",
    "superior",
    "effective",
    "effective performance",
    "improves",
    "improved",
    "improvement",
    "robust",
    "robustness",
    "reliable",
    "successfully",
    "success",
    "allows",
    "enable",
    "enables",
    "capable",
    "can detect",
    "we present",
    "we propose",
    "our method",
    "our system",
    "our approach",
    "high accuracy",
    "good performance",
    "strong generalization",
    "strong performance",
    "performs exceptionally",
    "performs well",
    "with new unseen data",
    "achieving",
    "accuracy of",
    "f1 score",
    "pr auc",
    "matthews correlation coefficient",
]


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _norm(text: str) -> str:
    return _normalize_space(text).lower()


def _tokens(text: str) -> set[str]:
    words = re.findall(
        r"[a-z0-9]+(?:-[a-z0-9]+)?",
        _norm(text),
    )
    return {
        word
        for word in words
        if len(word) > 2 and word not in STOPWORDS
    }



def _has_rural_health_context(text: str | None) -> bool:
    """Detect explicit rural/underserved healthcare context only."""
    normalized = _norm(text or "")
    if "rural" in normalized:
        return True
    non_rural_context = [
        term for term in RURAL_CONTEXT_TERMS if term != "rural"
    ]
    health_terms = [
        "healthcare", "health care", "medical", "medicine", "clinical",
        "diagnosis", "diagnostic", "patient", "hospital", "disease",
        "primary care", "community health",
    ]
    return any(term in normalized for term in non_rural_context) and any(
        term in normalized for term in health_terms
    )

def _phrase_present(phrase: str, text: str) -> bool:
    phrase_norm = _norm(phrase)
    text_norm = _norm(text)
    return bool(phrase_norm) and phrase_norm in text_norm


def _reconstruct_abstract(
    inverted_index: dict[str, list[int]] | None,
) -> str | None:
    if not inverted_index:
        return None

    ordered: list[tuple[int, str]] = []

    for word, positions in inverted_index.items():
        for position in positions:
            ordered.append((position, word))

    ordered.sort(key=lambda item: item[0])

    text = " ".join(word for _, word in ordered)
    return _normalize_space(text) or None


def _paper_record(work: dict[str, Any]) -> dict[str, Any]:
    primary_location = work.get("primary_location") or {}

    doi = work.get("doi")
    if doi:
        doi = doi.replace("https://doi.org/", "").strip()

    title = (
        work.get("display_name")
        or work.get("title")
        or "Untitled paper"
    )

    is_retracted = bool(work.get("is_retracted"))

    if "[retracted]" in _norm(title):
        is_retracted = True

    return {
        "id": work.get("id"),
        "title": title,
        "year": work.get("publication_year"),
        "doi": doi,
        "url": (
            primary_location.get("landing_page_url")
            or primary_location.get("pdf_url")
            or work.get("id")
        ),
        "cited_by_count": work.get("cited_by_count") or 0,
        "abstract": _reconstruct_abstract(
            work.get("abstract_inverted_index")
        ),
        "is_retracted": is_retracted,
    }


def _openalex_request(
    params: dict[str, Any],
) -> dict[str, Any]:
    response = httpx.get(
        OPENALEX_URL,
        params=params,
        timeout=25.0,
        headers={
            "User-Agent": (
                "ResearchMate-AI/1.0 "
                "(mailto:researchmate.ai@gmail.com)"
            )
        },
    )
    response.raise_for_status()
    return response.json()


def _crossref_request(params: dict[str, Any]) -> dict[str, Any]:
    response = httpx.get(
        CROSSREF_URL,
        params=params,
        timeout=25.0,
        headers={
            "User-Agent": (
                "ResearchMate-AI/1.0 "
                "(mailto:researchmate.ai@gmail.com)"
            )
        },
    )
    response.raise_for_status()
    return response.json()


def _strip_markup(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    return _normalize_space(value)


def search_crossref_evidence(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    params = {
        "query.bibliographic": query,
        "rows": min(max(limit, 1), 25),
        "select": (
            "DOI,title,published,author,abstract,URL,"
            "is-referenced-by-count,type,subtype"
        ),
        "mailto": CROSSREF_MAILTO,
    }

    payload = _crossref_request(params)
    items = (payload.get("message") or {}).get("items") or []

    output: list[dict[str, Any]] = []
    for item in items:
        title_values = item.get("title") or []
        title = _normalize_space(
            title_values[0] if title_values else "Untitled paper"
        )

        published = item.get("published") or item.get("published-print") or {}
        date_parts = published.get("date-parts") or []
        year = None
        if date_parts and date_parts[0]:
            try:
                year = int(date_parts[0][0])
            except (TypeError, ValueError):
                year = None

        doi = _normalize_space(str(item.get("DOI") or "")) or None
        url = item.get("URL") or (
            f"https://doi.org/{doi}" if doi else None
        )
        abstract = _strip_markup(item.get("abstract"))

        output.append({
            "id": f"crossref:{doi or title}",
            "title": title,
            "year": year,
            "doi": doi,
            "url": url,
            "cited_by_count": item.get("is-referenced-by-count") or 0,
            "abstract": abstract,
            "is_retracted": False,
        })

    return output


def search_openalex_evidence(
    query: str,
    limit: int = 20,
    *,
    min_year: int | None = None,
) -> list[dict[str, Any]]:
    base_params: dict[str, Any] = {
        "search": query,
        "per-page": min(max(limit, 1), 25),
        "sort": "relevance_score:desc",
        "mailto": OPENALEX_EMAIL,
    }

    if min_year:
        filtered_params = {
            **base_params,
            "filter": f"from_publication_date:{min_year}-01-01",
        }

        try:
            payload = _openalex_request(filtered_params)
        except Exception:
            payload = _openalex_request(base_params)
    else:
        payload = _openalex_request(base_params)

    return [
        _paper_record(work)
        for work in payload.get("results", [])
    ]


def _topic_profile(
    topic: str,
) -> dict[str, Any]:
    clean_topic = _normalize_space(topic)
    lower_topic = _norm(clean_topic)

    # Score all domains instead of stopping at the first match.
    domain_scores: list[tuple[int, str, list[str]]] = []

    for area, terms in DOMAIN_RULES:
        hits = [
            term
            for term in terms
            if term in lower_topic
        ]
        if hits:
            domain_scores.append(
                (len(hits), area, hits)
            )

    if domain_scores:
        domain_scores.sort(
            key=lambda item: item[0],
            reverse=True,
        )
        _, research_area, matched_domain_terms = domain_scores[0]
    else:
        research_area = "General Computer Science"
        matched_domain_terms = []

    task_hits: list[tuple[int, str]] = []

    for task_name, terms in TASK_RULES.items():
        hits = [
            term
            for term in terms
            if term in lower_topic
        ]
        if hits:
            task_hits.append(
                (len(hits), task_name)
            )

    task = None
    if task_hits:
        task_hits.sort(
            key=lambda item: item[0],
            reverse=True,
        )
        task = task_hits[0][1]

    methods = [
        method_name
        for method_name, terms in METHOD_RULES.items()
        if any(term in lower_topic for term in terms)
    ]

    context_terms = [
        term
        for term in CONTEXT_RULES
        if term in lower_topic
    ]

    outcome_terms = [
        term
        for term in OUTCOME_RULES
        if term in lower_topic
    ]

    components = {
        "task": bool(task),
        "method": bool(methods),
        "context": bool(context_terms),
        "outcome": bool(outcome_terms),
        "object_or_domain": bool(matched_domain_terms),
    }

    specificity_score = round(
        100 * sum(components.values()) / len(components),
        1,
    )

    missing_dimensions = [
        name.replace("_", " ").title()
        for name, available in components.items()
        if not available
    ]

    # A topic cannot be called "Highly Specific" while a core dimension
    # such as outcome is still missing.
    missing_count = len(missing_dimensions)

    if missing_count >= 3 or specificity_score < 40:
        specificity = "Needs More Specificity"
    elif missing_count >= 1 or specificity_score < 80:
        specificity = "Moderately Specific"
    else:
        specificity = "Highly Specific"

    return {
        "topic": clean_topic,
        "research_area": research_area,
        "task": task,
        "methods": methods,
        "context_terms": context_terms,
        "outcome_terms": outcome_terms,
        "domain_terms": matched_domain_terms,
        "specificity_score": specificity_score,
        "specificity": specificity,
        "missing_dimensions": missing_dimensions,
    }


def _search_variants(
    profile: dict[str, Any],
) -> list[str]:
    topic = profile["topic"]
    variants = [topic]

    # Add concept-aware queries rather than requiring every word to occur
    # together in a single OpenAlex result.
    if profile["methods"] and profile["task"]:
        variants.append(
            f"{profile['methods'][0]} {profile['task']}"
        )

    if profile["methods"] and profile["research_area"]:
        variants.append(
            f"{profile['methods'][0]} {profile['research_area']}"
        )

    if profile["methods"] and profile["context_terms"]:
        variants.append(
            f"{profile['methods'][0]} {profile['context_terms'][0]} healthcare"
        )

    if profile["task"] and profile["research_area"]:
        variants.append(
            f"{profile['task']} {profile['research_area']}"
        )

    # Synonym expansions for high-value research concepts.
    lower_topic = _norm(topic)

    if "explainable ai" in lower_topic or "xai" in lower_topic or "explainability" in lower_topic:
        variants.extend(
            [
                "explainable AI healthcare diagnosis",
                "XAI medical diagnosis",
                "explainable artificial intelligence clinical diagnosis",
                "interpretable machine learning healthcare",
                "explainable AI clinical medicine",
            ]
        )

    if "rural" in lower_topic:
        variants.extend(
            [
                "rural healthcare AI diagnosis",
                "rural health artificial intelligence",
                "rural healthcare machine learning diagnosis",
            ]
        )

    if "weapon" in lower_topic:
        variants.extend(
            [
                "weapon detection surveillance",
                "weapon detection deep learning",
                "weapon detection CCTV",
            ]
        )

    if "face detection" in lower_topic:
        variants.extend(
            [
                "face detection",
                "robust face detection",
                "real-time face detection",
                "face detection deep learning",
            ]
        )

    if any(term in lower_topic for term in [
        "helmet detection",
        "safety helmet",
        "helmet violation",
    ]):
        variants.extend(
            [
                "helmet detection motorcycle traffic",
                "motorcycle helmet detection",
                "safety helmet detection deep learning",
                "helmet detection YOLO real time",
                "helmet violation detection CCTV",
            ]
        )

    cleaned: list[str] = []

    for value in variants:
        value = _normalize_space(value)
        if value and value not in cleaned:
            cleaned.append(value)

    return cleaned[:10]


def _dedupe_papers(
    papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []

    for paper in papers:
        raw_key = (
            paper.get("doi")
            or paper.get("title")
            or paper.get("id")
            or ""
        )

        key = _norm(str(raw_key))

        if not key or key in seen:
            continue

        seen.add(key)
        output.append(paper)

    return output


def _topic_concept_families(
    profile: dict[str, Any],
) -> dict[str, set[str]]:
    topic = _norm(profile["topic"])

    families: dict[str, set[str]] = {
        "task": set(
            TASK_RULES.get(
                profile["task"],
                [],
            )
            if profile["task"]
            else []
        ),
        "method": set(),
        "domain": set(),
        "context": set(),
        "outcome": set(),
    }

    for method in profile["methods"]:
        families["method"].update(
            METHOD_RULES.get(method, [])
        )

    families["domain"].update(
        DOMAIN_RULES[
            next(
                (
                    index
                    for index, (area, _) in enumerate(DOMAIN_RULES)
                    if area == profile["research_area"]
                ),
                0,
            )
        ][1]
        if profile["research_area"] != "General Computer Science"
        else []
    )

    families["context"].update(
        profile["context_terms"]
    )

    families["outcome"].update(
        profile["outcome_terms"]
    )

    # Add explicit topic phrase as a strong cue.
    families["topic"] = {topic}

    return families


def _paper_relevance(
    topic: str,
    profile: dict[str, Any],
    paper: dict[str, Any],
) -> dict[str, Any]:
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    combined = f"{title}. {abstract}"
    combined_norm = _norm(combined)
    families = _topic_concept_families(profile)
    score = 0.0
    evidence: list[str] = []

    exact_topic_title = _phrase_present(topic, title)
    exact_topic_abstract = _phrase_present(topic, abstract)
    if exact_topic_title:
        score += 32
        evidence.append("exact topic phrase in title")
    elif exact_topic_abstract:
        score += 22
        evidence.append("exact topic phrase in abstract")

    task_hits = sum(1 for term in families["task"] if term in combined_norm)
    method_hits = sum(1 for term in families["method"] if term in combined_norm)
    domain_hits = sum(1 for term in families["domain"] if term in combined_norm)
    context_hits = sum(1 for term in families["context"] if term in combined_norm)
    outcome_hits = sum(1 for term in families["outcome"] if term in combined_norm)

    if task_hits:
        score += min(24, 18 + 2 * (task_hits - 1)); evidence.append("task match")
    if method_hits:
        score += min(22, 16 + 2 * (method_hits - 1)); evidence.append("method match")
    if domain_hits:
        score += min(18, 10 + 2 * (domain_hits - 1)); evidence.append("domain match")
    if context_hits:
        score += min(10, 5 + context_hits); evidence.append("context match")
    if outcome_hits:
        score += min(7, 3 + outcome_hits); evidence.append("outcome match")

    topic_tokens = _tokens(topic)
    title_tokens = _tokens(title)
    abstract_tokens = _tokens(abstract)
    score += 10 * len(topic_tokens & title_tokens) / max(len(topic_tokens), 1)
    score += 5 * len(topic_tokens & abstract_tokens) / max(len(topic_tokens), 1)

    lower_topic = _norm(topic)
    if any(p in lower_topic for p in ["explainable ai", "xai", "explainability"]) and any(
        t in combined_norm for t in [
            "explainable ai", "explainable artificial intelligence", "xai",
            "interpretable", "interpretability", "explainability"
        ]
    ):
        score += 8; evidence.append("XAI synonym match")

    if "diagnos" in lower_topic and any(
        t in combined_norm for t in ["diagnosis", "diagnostic", "clinical decision", "disease prediction"]
    ):
        score += 8; evidence.append("diagnosis synonym match")

    if "healthcare" in lower_topic and any(
        t in combined_norm for t in ["healthcare", "health care", "clinical", "medical", "medicine"]
    ):
        score += 6; evidence.append("healthcare synonym match")

    score = round(max(0.0, min(99.0, score)), 1)
    if score >= 85:
        label = "Highly relevant"
    elif score >= 70:
        label = "Relevant"
    elif score >= 55:
        label = "Related"
    else:
        label = "Weak / excluded"

    # Primary relevance gate: a specialized task must actually match the
    # retrieved paper; a defined method/domain/context must have at least one
    # topical overlap unless the exact topic phrase is present.
    topical_gate = True
    gate_reason = "general topical match"
    if profile.get("task"):
        topical_gate = bool(task_hits)
        if topical_gate and (
            profile.get("methods") or profile.get("domain_terms") or profile.get("context_terms")
        ):
            topical_gate = bool(
                method_hits or domain_hits or context_hits or exact_topic_title or exact_topic_abstract
            )
        gate_reason = "task and topical-context match" if topical_gate else "missing task or topical-context match"

    primary_relevant = (
        bool(exact_topic_title or exact_topic_abstract)
        or (topical_gate and score >= 55)
    )

    return {
        "score": score,
        "label": label,
        "primary_relevant": primary_relevant,
        "reason": ", ".join(dict.fromkeys(evidence + [gate_reason])) if evidence else gate_reason,
    }


def _rank_and_filter_papers(
    topic: str,
    profile: dict[str, Any],
    papers: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    for paper in papers:
        relevance = _paper_relevance(topic, profile, paper)
        paper["relevance_score"] = relevance["score"]
        paper["relevance_label"] = relevance["label"]
        paper["relevance_reason"] = relevance["reason"]
        paper["primary_relevant"] = relevance["primary_relevant"]
        paper["rural_evidence"] = _has_rural_health_context(
            f"{paper.get('title') or ''} {paper.get('abstract') or ''}"
        )

    retrieved_count = len(papers)
    eligible = [p for p in papers if not p.get("is_retracted")]
    relevant = [p for p in eligible if p.get("primary_relevant")]
    relevant.sort(
        key=lambda p: (
            p.get("relevance_score", 0.0),
            p.get("year", 0) or 0,
            p.get("cited_by_count", 0) or 0,
        ),
        reverse=True,
    )
    return relevant[:30], retrieved_count, len(relevant)

def retrieve_literature(topic: str) -> dict[str, Any]:
    cache_key = _norm(topic)
    cached = _CACHE.get(cache_key)
    if cached:
        created_at, data = cached
        if datetime.utcnow() - created_at < CACHE_TTL:
            return data

    profile = _topic_profile(topic)
    variants = _search_variants(profile)
    current_year = date.today().year
    recent_threshold = current_year - 4
    papers: list[dict[str, Any]] = []
    provider_errors: list[str] = []
    openalex_success_count = 0
    crossref_success_count = 0

    for query in variants:
        try:
            results = search_openalex_evidence(query, limit=20, min_year=recent_threshold)
            openalex_success_count += 1
            papers.extend(results)
        except Exception as exc:
            provider_errors.append(f"OpenAlex recent search '{query}': {exc}")

    for query in variants:
        try:
            results = search_openalex_evidence(query, limit=20, min_year=None)
            openalex_success_count += 1
            papers.extend(results)
        except Exception as exc:
            provider_errors.append(f"OpenAlex broad search '{query}': {exc}")

    papers = _dedupe_papers(papers)

    if not papers:
        for query in variants[:6]:
            try:
                results = search_crossref_evidence(query, limit=20)
                if results:
                    crossref_success_count += 1
                    papers.extend(results)
            except Exception as exc:
                provider_errors.append(f"Crossref fallback search '{query}': {exc}")
        papers = _dedupe_papers(papers)

    relevant_papers, retrieved_count, relevant_count = _rank_and_filter_papers(
        topic, profile, papers
    )
    recent_relevant_count = sum(
        1 for paper in relevant_papers
        if (paper.get("year") or 0) >= recent_threshold
    )
    retracted_count = sum(1 for paper in papers if paper.get("is_retracted"))
    rural_specific_papers = [p for p in relevant_papers if p.get("rural_evidence")]
    rural_specific_recent_count = sum(
        1 for p in rural_specific_papers
        if (p.get("year") or 0) >= recent_threshold
    )

    provider = (
        "OpenAlex + Crossref fallback" if openalex_success_count and crossref_success_count
        else "OpenAlex" if openalex_success_count
        else "Crossref fallback" if crossref_success_count
        else "Unavailable"
    )
    if relevant_count > 0:
        search_status = "success"
    elif papers:
        search_status = "no_relevant_records"
    elif provider_errors:
        search_status = "provider_error"
    else:
        search_status = "empty"

    result = {
        "profile": profile,
        "queries": variants,
        "papers": relevant_papers,
        "retrieved_count": retrieved_count,
        "relevant_count": relevant_count,
        "recent_count": recent_relevant_count,
        "retracted_count": retracted_count,
        "rural_specific_count": len(rural_specific_papers),
        "rural_specific_recent_count": rural_specific_recent_count,
        "rural_specific_papers": [
            {
                "title": p.get("title"), "year": p.get("year"),
                "doi": p.get("doi"), "url": p.get("url"),
                "relevance_score": p.get("relevance_score"),
            }
            for p in rural_specific_papers[:12]
        ],
        "provider": provider,
        "search_status": search_status,
        "provider_errors": provider_errors,
        "provider_status": {
            "openalex_successful_queries": openalex_success_count,
            "crossref_fallback_successful_queries": crossref_success_count,
            "has_records": bool(papers),
            "has_relevant_records": bool(relevant_papers),
        },
    }
    _CACHE[cache_key] = (datetime.utcnow(), result)
    return result

def _sentence_fragments(
    text: str | None,
) -> list[str]:
    if not text:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+|\n+",
        text,
    )

    return [
        _normalize_space(part)
        for part in parts
        if len(_normalize_space(part)) >= 45
    ]


def _classify_evidence_sentence(
    sentence: str,
) -> dict[str, str] | None:
    lower = _norm(sentence)

    matched_gap_markers = [
        term
        for terms in GAP_PATTERNS.values()
        for term in terms
        if term in lower
    ]

    if not matched_gap_markers:
        return None

    is_future_work = any(
        term in lower
        for term in FUTURE_WORK_TERMS
    )

    is_explicit_limitation = any(
        term in lower
        for term in EXPLICIT_LIMITATION_TERMS
    )

    is_positive_result = any(
        term in lower
        for term in POSITIVE_RESULT_TERMS
    )

    # These markers describe a documented limitation/challenge rather than
    # a positive solution statement. Generic words such as "problem" or
    # "issue" are intentionally excluded because they often occur in
    # sentences that merely introduce the field or a proposed solution.
    explicit_challenge_markers = [
        "challenging",
        "challenge",
        "difficulty",
        "difficult",
        "bottleneck",
        "obstacle",
        "barrier",
        "remain difficult",
        "remains difficult",
        "lack of",
        "limited",
        "cannot",
        "unable",
        "not able",
        "fails to",
        "failure to",
        "underperform",
        "underperforms",
        "not validated",
        "not generalize",
        "does not generalize",
        "generalization remains",
        "generalisation remains",
    ]

    is_field_challenge = any(
        term in lower
        for term in explicit_challenge_markers
    )

    # Positive findings are never gap evidence unless the same sentence
    # explicitly states a limitation/failure/future-work problem.
    if is_positive_result and not (
        is_future_work
        or is_explicit_limitation
        or is_field_challenge
    ):
        return None

    # A generic statement such as "data quality is imperative" is not a
    # research limitation or a challenge by itself.
    if not (
        is_future_work
        or is_explicit_limitation
        or is_field_challenge
    ):
        return None

    # Avoid phrases where the theme is merely mentioned in a successful
    # deployment/result statement (e.g. "strong generalization").
    if (
        "generalization" in lower
        or "generalisation" in lower
    ) and (
        is_positive_result
        and not any(
            term in lower
            for term in [
                "lack of generalization",
                "lack of generalisation",
                "poor generalization",
                "poor generalisation",
                "limited generalization",
                "limited generalisation",
                "generalization challenge",
                "generalisation challenge",
                "generalization remains",
                "generalisation remains",
                "does not generalize",
                "not validated",
            ]
        )
    ):
        return None

    if is_future_work:
        evidence_type = "Future-work signal"
    elif is_explicit_limitation:
        evidence_type = "Reported limitation"
    else:
        evidence_type = "Field challenge"

    return {
        "evidence_type": evidence_type,
    }


def _gap_evidence(literature: dict[str, Any]) -> list[dict[str, Any]]:
    profile = literature.get("profile") or {}
    topic = _norm(profile.get("topic") or "")
    is_rural_topic = "rural" in topic
    theme_papers: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    theme_evidence: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for paper in literature.get("papers", []):
        if paper.get("is_retracted"):
            continue
        abstract = paper.get("abstract") or ""
        for sentence in _sentence_fragments(abstract):
            classified = _classify_evidence_sentence(sentence)
            if not classified:
                continue
            lower_sentence = _norm(sentence)
            for theme, patterns in GAP_PATTERNS.items():
                if not any(pattern in lower_sentence for pattern in patterns):
                    continue
                if theme == "rural and underserved validation" and not _has_rural_health_context(
                    f"{paper.get('title') or ''} {abstract}"
                ):
                    continue
                theme_papers[theme].append(paper)
                theme_evidence[theme].append({
                    "sentence": sentence[:500],
                    "evidence_type": classified["evidence_type"],
                    "paper_id": paper.get("id"),
                    "is_rural_specific": bool(paper.get("rural_evidence")),
                })

    evidence: list[dict[str, Any]] = []
    for theme, supporting in theme_papers.items():
        unique_by_id: dict[Any, dict[str, Any]] = {}
        for paper in supporting:
            unique_by_id[paper.get("id")] = paper
        if len(unique_by_id) < 2:
            continue

        snippets: list[dict[str, Any]] = []
        seen_snippets: set[tuple[Any, str]] = set()
        for item in theme_evidence[theme]:
            key = (item["paper_id"], item["sentence"])
            if key in seen_snippets:
                continue
            seen_snippets.add(key)
            snippets.append(item)
            if len(snippets) >= 6:
                break

        rural_support_count = sum(
            1 for paper in unique_by_id.values()
            if paper.get("rural_evidence")
        )
        if rural_support_count == len(unique_by_id):
            evidence_scope = "Rural-specific"
        elif rural_support_count == 0:
            evidence_scope = "General literature"
        else:
            evidence_scope = "Mixed: general + rural-specific"

        type_counts = defaultdict(int)
        for snippet in snippets:
            type_counts[snippet["evidence_type"]] += 1
        strongest_type = (
            "Reported limitation" if type_counts["Reported limitation"]
            else "Future-work signal" if type_counts["Future-work signal"]
            else "Field challenge"
        )

        theme_label = theme.title()
        evidence.append({
            "theme": theme,
            "theme_label": theme_label,
            "gap": (
                f"{theme_label} is a candidate research direction supported by "
                "repeated explicit limitation or future-work evidence in the "
                "retrieved literature."
                + (
                    " Rural-specific applicability remains unverified."
                    if is_rural_topic and evidence_scope == "General literature"
                    else ""
                )
            ),
            "evidence_strength": strongest_type,
            "supporting_paper_count": len(unique_by_id),
            "evidence_type": strongest_type,
            "evidence_scope": evidence_scope,
            "rural_specific_supporting_paper_count": rural_support_count,
            "supporting_papers": [
                {
                    "title": p.get("title"), "year": p.get("year"),
                    "doi": p.get("doi"), "url": p.get("url"),
                    "relevance_score": p.get("relevance_score"),
                }
                for p in list(unique_by_id.values())[:6]
            ],
            "evidence_snippets": snippets,
        })

    rank = {"Reported limitation": 3, "Future-work signal": 2, "Field challenge": 1}
    evidence.sort(
        key=lambda item: (
            rank.get(item.get("evidence_type", ""), 0),
            item.get("rural_specific_supporting_paper_count", 0),
            item.get("supporting_paper_count", 0),
        ),
        reverse=True,
    )
    return evidence[:5]

def build_novelty_evidence(
    literature: dict[str, Any],
) -> dict[str, Any]:
    papers = literature.get("papers", [])

    if not papers:
        return {
            "novelty_score": None,
            "novelty_level": "Not established",
            "assessment": (
                "No eligible academic evidence was retrieved, so a "
                "prior-art signal cannot be established from this search."
            ),
            "evidence_count": 0,
            "recent_evidence_count": 0,
            "evidence_papers": [],
        }

    top_papers = papers[:12]

    scores = [
        float(paper.get("relevance_score", 0) or 0)
        for paper in top_papers
    ]
    strong_count = sum(
        1
        for score in scores
        if score >= 80
    )
    average_score = (
        sum(scores) / max(len(scores), 1)
    )

    # Use a descriptive literature-overlap label rather than implying that
    # the retrieval score is a measured novelty value.
    if strong_count >= 8 and average_score >= 78:
        level = "High literature overlap signal"
    elif strong_count >= 4 and average_score >= 70:
        level = "Moderate literature overlap signal"
    else:
        level = "Limited literature overlap signal"

    evidence_papers = []

    for paper in top_papers:
        evidence_papers.append(
            {
                "title": paper.get("title"),
                "year": paper.get("year"),
                "doi": paper.get("doi"),
                "url": paper.get("url"),
                "overlap_signal": paper.get(
                    "relevance_score",
                    0,
                ),
                "relevance_label": paper.get(
                    "relevance_label"
                ),
                "relevance_reason": paper.get(
                    "relevance_reason"
                ),
                "cited_by_count": paper.get(
                    "cited_by_count",
                    0,
                )
                or 0,
                "id": paper.get("id"),
            }
        )

    return {
        "novelty_score": None,
        "novelty_level": level,
        "assessment": (
            "This is a literature-relevance signal, not a novelty score. "
            "Retrieved records are ranked using task, method, domain, "
            "context and lexical evidence. A defensible novelty claim "
            "requires broader comparison of recent methods, datasets, "
            "evaluation settings, baselines and limitations."
        ),
        "evidence_count": literature.get(
            "relevant_count",
            len(papers),
        ),
        "recent_evidence_count": literature.get(
            "recent_count",
            0,
        ),
        "evidence_papers": evidence_papers,
    }


def build_gap_evidence(
    literature: dict[str, Any],
) -> dict[str, Any]:
    evidence = _gap_evidence(literature)

    if not evidence:
        return {
            "identified_gaps": [],
            "confirmed_gap_count": 0,
            "gap_summary": (
                "No cross-paper research gap was established from "
                "repeated explicit limitation, future-work, or field "
                "challenge evidence across the retrieved non-retracted papers."
            ),
            "research_direction": (
                "Define a specific intervention and measurable outcome, "
                "then validate a candidate gap against full-text literature "
                "before presenting it as unresolved."
            ),
            "evidence": [],
        }

    return {
        "identified_gaps": [
            item.get("theme_label") or item["gap"]
            for item in evidence
        ],
        "confirmed_gap_count": len(evidence),
        "gap_summary": (
            "The retrieved non-retracted literature contains repeated "
            "evidence themes. These are candidate research directions, "
            "not proof that the underlying problem is unsolved or novel."
        ),
        "research_direction": (
            "Select one repeated limitation or future-work theme, define "
            "a measurable intervention and evaluation protocol, and verify "
            "the claim against full-text literature."
        ),
        "evidence": evidence,
    }


def _clean_phrase(value: str) -> str:
    value = re.sub(
        r"\[[^\]]+\]",
        "",
        value,
    )
    value = re.sub(
        r"[^a-zA-Z0-9&+./ -]",
        " ",
        value,
    )
    return _normalize_space(value)


def build_keywords(profile: dict[str, Any], literature: dict[str, Any]) -> list[str]:
    """Return deterministic concept phrases suitable for the next search."""
    topic = _norm(profile.get("topic") or "")
    area = profile.get("research_area") or ""
    task = profile.get("task")
    methods = profile.get("methods") or []
    contexts = profile.get("context_terms") or []
    outcomes = profile.get("outcome_terms") or []
    keywords: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        clean = _clean_phrase(_normalize_space(str(value or "")))
        if not clean or clean.lower() in seen:
            return
        seen.add(clean.lower())
        keywords.append(clean)

    if "helmet" in topic:
        controlled = [
            "helmet detection", "safety helmet", "motorcycle", "motorcyclist",
            "traffic safety", "object detection", "computer vision", "deep learning",
            "YOLO", "real-time detection", "occlusion", "low-light", "adverse weather",
        ]
    elif "weapon" in topic:
        controlled = [
            "weapon detection", "surveillance", "CCTV", "object detection",
            "computer vision", "deep learning", "real-time detection", "occlusion", "robustness",
        ]
    elif any(x in topic for x in ["explainable ai", "xai", "explainability"]):
        controlled = [
            "explainable AI", "XAI", "interpretability",
            "clinical usability" if "healthcare" in topic else "model interpretability",
            "diagnosis" if task == "diagnosis" else "machine learning",
            "healthcare" if "healthcare" in topic else "artificial intelligence",
            "external validation" if "rural" in topic else "generalization",
        ]
        if "rural" in topic:
            controlled += ["rural healthcare", "rural health", "underserved populations"]
    elif "Healthcare" in area:
        controlled = [
            "healthcare",
            "medical diagnosis" if task == "diagnosis" else "clinical AI",
            "clinical diagnosis" if task == "diagnosis" else "clinical decision support",
            "external validation", "generalization",
        ]
    elif "Traffic Safety" in area:
        controlled = ["traffic safety", "computer vision", "object detection", "deep learning", "real-time detection"]
    else:
        controlled = []

    for item in controlled:
        add(item)
    for item in methods[:3] + contexts[:3] + outcomes[:3]:
        add(item)
    return keywords[:14]

def build_research_questions(profile: dict[str, Any], gaps: dict[str, Any]) -> dict[str, Any]:
    topic = profile["topic"]
    lower_topic = _norm(topic)
    contexts = profile.get("context_terms") or []
    methods = profile.get("methods") or []

    if "helmet" in lower_topic:
        questions = [
            "How accurately can motorcycle helmet use be detected in traffic scenes using computer-vision methods?",
            "Which object-detection architectures provide an appropriate trade-off between helmet-detection accuracy and real-time inference?",
            "How do occlusion, multiple riders, low-light conditions and adverse weather affect helmet-detection robustness?",
            "Which datasets, baselines and evaluation metrics are needed for a reproducible comparison of helmet-detection systems across traffic scenes?",
            "Which limitation is repeatedly reported in the retrieved helmet-detection literature and can be tested through a clearly defined intervention?",
        ]
    elif profile.get("task") == "diagnosis":
        is_rural = "rural" in lower_topic or "rural" in " ".join(contexts).lower()
        context_phrase = "rural healthcare settings" if is_rural else "the selected healthcare setting"
        explainable = any("explainable" in _norm(m) or "xai" in _norm(m) for m in methods)
        method_phrase = "the selected explainable AI method" if explainable else "the selected AI method"
        questions = [
            f"How can diagnosis in {context_phrase} be evaluated using clearly defined technical and clinical criteria?",
            f"Which method or baseline should be compared with {method_phrase} to measure diagnostic performance and explanation quality reproducibly?",
            "How do dataset composition, population characteristics and data quality affect diagnostic performance and external validity?",
            "What measurable outcomes should be used to assess diagnostic performance, explanation quality and clinical usability?",
            "Which limitation in the retrieved literature should be selected for intervention-level testing, and does that limitation remain applicable in the target healthcare context?",
        ]
    else:
        task = profile.get("task")
        contexts_text = ", ".join(contexts[:3])
        method_text = methods[0] if methods else "the selected method"
        questions = [
            f"How can {task} be evaluated effectively for {topic} using evidence-supported methods?" if task else f"What specific research task should be investigated for {topic}, and how should success be measured?",
            f"Which {method_text} or alternative method should be compared using recent reproducible baselines?",
            f"How do dataset composition, data quality and the identified context ({contexts_text}) affect measured performance and reliability?" if contexts_text else "How do dataset composition, data quality and evaluation settings affect measured performance?",
            "Which measurable outcomes and operating conditions should be fixed to make the study reproducible and testable?",
            "Which repeated limitation or future-work theme in the retrieved non-retracted literature should be selected for focused investigation?",
        ]

    complete = bool(profile.get("task") and profile.get("methods") and profile.get("outcome_terms"))
    if complete:
        hypothesis = "The selected method will improve the predefined outcome(s) for the specified task and dataset compared with a reproducible baseline, subject to empirical validation."
        variables = [
            "Independent Variable: Selected methodology / model variant",
            "Dependent Variable: Predefined task outcome",
            "Evaluation Metrics: " + ", ".join(profile["outcome_terms"][:5]),
            "Dataset: Explicitly defined training/validation/test data",
            "Baseline: Recent reproducible baseline",
        ]
    else:
        hypothesis = "A testable hypothesis should be finalized only after the research task, intervention/model, context and measurable outcome are explicitly defined."
        variables = [
            "Independent Variable: Not yet defined",
            "Dependent Variable: Not yet defined",
            "Evaluation Metrics: Not yet defined",
            "Dataset: Not yet defined",
            "Baseline: Not yet defined",
        ]
    return {
        "research_questions": questions[:5],
        "hypothesis": hypothesis,
        "variables": variables,
        "research_direction": "Complete the missing research dimensions, select a measurable outcome, choose a reproducible baseline, and test the selected research direction against the retrieved evidence.",
    }


def _suggested_outcomes(profile: dict[str, Any]) -> list[dict[str, str]]:
    if profile.get("task") == "diagnosis":
        values = [
            ("Diagnostic performance", "accuracy, F1, sensitivity, specificity or AUROC as appropriate"),
            ("Clinical reliability", "calibration, error analysis or external validation"),
            ("Explanation quality", "fidelity, stability or another explicitly defined explanation criterion"),
            ("Clinical usability", "user study or structured clinician assessment when applicable"),
        ]
    elif profile.get("task") == "detection":
        values = [
            ("Detection performance", "precision, recall, F1 or mAP as appropriate to the detector"),
            ("Robustness", "performance under occlusion, lighting or environmental shifts"),
            ("Real-time performance", "latency or FPS under a stated hardware configuration"),
        ]
    elif profile.get("task") == "classification":
        values = [
            ("Classification performance", "accuracy, precision, recall, F1 or AUROC as appropriate"),
            ("Robustness", "performance across relevant dataset or deployment shifts"),
        ]
    else:
        values = [
            ("Primary task outcome", "one predefined metric directly measuring the research objective"),
            ("Generalization", "performance on a clearly separated evaluation setting"),
        ]
    return [
        {"name": name, "description": desc, "source": "AI suggestion; not extracted from a paper"}
        for name, desc in values
    ]

def build_feasibility(
    profile: dict[str, Any],
) -> dict[str, Any]:
    score = 50.0
    topic = profile["topic"].lower()

    if profile["task"]:
        score += 10

    if profile["methods"]:
        score += 5

    if profile["outcome_terms"]:
        score += 10
    else:
        score -= 5

    if profile["context_terms"]:
        score += 5

    if profile["domain_terms"]:
        score += 5

    if len(profile["topic"]) >= 40:
        score += 5

    if any(
        term in topic
        for term in [
            "multimodal",
            "large language model",
            "llm",
            "video",
            "real-time",
            "real time",
            "federated",
        ]
    ):
        score -= 10

    score = max(
        0.0,
        min(
            100.0,
            round(score, 1),
        ),
    )

    dataset_feasibility = (
        "Moderate"
        if profile["task"]
        else "Needs definition"
    )

    computational_feasibility = (
        "Moderate"
        if profile["methods"]
        else "Not yet established"
    )

    implementation_complexity = (
        "High"
        if any(
            term in topic
            for term in [
                "real-time",
                "real time",
                "multimodal",
                "federated",
                "edge ai",
            ]
        )
        else (
            "Moderate"
            if profile["task"] or profile["methods"]
            else "Not yet established"
        )
    )

    evaluation_feasibility = (
        "Moderate to High"
        if profile["outcome_terms"]
        else "Needs measurable metrics"
    )

    # Missing a core dimension prevents a "Potentially Feasible" label.
    if (
        score >= 75
        and not any(
            [
                not profile["task"],
                not profile["methods"],
                not profile["outcome_terms"],
            ]
        )
    ):
        overall = "Potentially Feasible"
    elif score >= 50:
        overall = "Conditionally Feasible"
    else:
        overall = "Needs Further Definition"

    challenges = []

    if not profile["task"]:
        challenges.append(
            "Research task is not explicitly defined."
        )

    if not profile["methods"]:
        challenges.append(
            "Method or model family is not explicitly defined."
        )

    if not profile["outcome_terms"]:
        challenges.append(
            "Measurable evaluation outcomes are not explicitly defined."
        )

    if not profile["context_terms"]:
        challenges.append(
            "Deployment context is not explicitly defined."
        )

    recommendations = [
        "Define the task and measurable success criteria.",
        "Select a reproducible baseline from recent literature.",
        "Specify dataset, evaluation split and experimental constraints.",
    ]

    return {
        "research_area": profile["research_area"],
        "dataset_feasibility": dataset_feasibility,
        "computational_feasibility": computational_feasibility,
        "implementation_complexity": implementation_complexity,
        "evaluation_feasibility": evaluation_feasibility,
        "overall_feasibility": overall,
        "feasibility_score": score,
        "challenges": challenges,
        "recommendations": recommendations,
    }


def analyze_topic_with_evidence(
    topic: str,
) -> dict[str, Any]:
    literature = retrieve_literature(topic)
    profile = literature["profile"]

    novelty = build_novelty_evidence(literature)
    gap = build_gap_evidence(literature)
    questions = build_research_questions(profile, gap)
    feasibility = build_feasibility(profile)
    keywords = build_keywords(profile, literature)
    suggested_outcomes = _suggested_outcomes(profile)

    rural_specific_count = literature.get(
        "rural_specific_count",
        0,
    )
    rural_specific_recent_count = literature.get(
        "rural_specific_recent_count",
        0,
    )

    provider = literature.get("provider") or "Unavailable"
    provider_status = literature.get("provider_status") or {}
    has_evidence = bool(literature.get("papers"))

    if not has_evidence:
        if literature.get("provider_errors"):
            evidence_note = (
                "Academic evidence retrieval is currently unavailable. "
                "The configured literature providers did not return usable "
                "records for this request. This must not be interpreted as "
                "evidence of novelty or absence of prior work."
            )
        else:
            evidence_note = (
                "No sufficiently relevant academic records were returned "
                "by the configured literature providers for this query. "
                "This is an evidence-coverage result, not proof of novelty."
            )
    elif "rural" in profile["topic"].lower():
        if rural_specific_count:
            evidence_note = (
                f"Evidence source: {provider}. "
                f"{rural_specific_count} relevant records explicitly mention "
                "rural/remote/underserved healthcare context; "
                f"{rural_specific_recent_count} are recent."
            )
        else:
            evidence_note = (
                f"Evidence source: {provider}. Relevant healthcare/XAI "
                "records were retrieved, but no relevant records in the "
                "current result set explicitly establish a rural-specific "
                "evidence base. General healthcare/XAI evidence should not be "
                "treated as rural-specific evidence."
            )
    else:
        evidence_note = (
            f"Evidence source: {provider}. The retrieved records support "
            "preliminary literature screening; they do not by themselves "
            "establish novelty or a definitive research gap."
        )

    topic_result = {
        "topic": profile["topic"],
        "research_field": profile["research_area"],
        "specificity": profile["specificity"],
        "feasibility": feasibility[
            "overall_feasibility"
        ],
        "keywords": keywords,
        "validation_summary": (
            "The topic was screened across task, method, context, outcome "
            "and domain dimensions. Multiple concept-aware searches were "
            "used for preliminary prior-art comparison. Literature evidence "
            "is reported only when the configured provider returned usable "
            "records."
        ),
        "specificity_score": profile[
            "specificity_score"
        ],
        "missing_dimensions": profile[
            "missing_dimensions"
        ],
        "topic_profile": profile,
        "evidence_note": evidence_note,
        "suggested_outcomes": suggested_outcomes if not profile.get("outcome_terms") else [],
    }

    novelty = {
        **novelty,
        "topic": profile["topic"],
        "research_area": profile["research_area"],
        "potential_gap": (
            gap["identified_gaps"][0]
            if gap["identified_gaps"]
            else "No evidence-backed cross-paper gap established."
        ),
        "recommendation": (
            "Compare recent methods, datasets, evaluation settings, "
            "baselines and limitations before making a novelty claim."
        ),
        "retracted_excluded_count": literature.get(
            "retracted_count",
            0,
        ),
        "rural_specific_count": rural_specific_count,
        "rural_specific_recent_count": rural_specific_recent_count,
    }

    if (
        "rural" in profile["topic"].lower()
        and rural_specific_count == 0
    ):
        novelty["assessment"] += (
            " The current relevant set does not establish rural-specific "
            "evidence; this should be treated as an evidence-coverage issue, "
            "not as proof of novelty."
        )

    gap = {
        **gap,
        "topic": profile["topic"],
        "research_area": profile["research_area"],
        "retracted_excluded_count": literature.get(
            "retracted_count",
            0,
        ),
    }

    questions = {
        **questions,
        "topic": profile["topic"],
        "research_area": profile["research_area"],
    }

    feasibility = {
        **feasibility,
        "topic": profile["topic"],
    }

    return {
        "topic": topic_result,
        "novelty": novelty,
        "gap": gap,
        "questions": questions,
        "feasibility": feasibility,
        "literature": {
            "provider": literature["provider"],
            "provider_status": literature.get("provider_status", {}),
            "provider_errors": literature.get("provider_errors", []),
            "papers": novelty["evidence_papers"],
            "retrieved_count": literature.get(
                "retrieved_count",
                0,
            ),
            "relevant_count": literature.get(
                "relevant_count",
                0,
            ),
            "recent_count": literature.get(
                "recent_count",
                0,
            ),
            "retracted_count": literature.get(
                "retracted_count",
                0,
            ),
            "rural_specific_count": rural_specific_count,
            "rural_specific_recent_count": rural_specific_recent_count,
            "rural_specific_papers": literature.get(
                "rural_specific_papers",
                [],
            ),
            "queries": literature.get(
                "queries",
                [],
            ),
            "provider_errors": literature.get("provider_errors", []),
            "search_status": literature.get("search_status", "success"),
        },
        "evidence_note": evidence_note,
    }
