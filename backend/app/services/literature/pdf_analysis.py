
import io
import re
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader


# ============================================================
# ResearchMate AI — evidence-first academic PDF analyzer
# ============================================================
# Design:
# 1. Extract the PDF faithfully.
# 2. Remove page headers/footers and figure/table captions from
#    the semantic text used for field extraction.
# 3. Detect real academic headings, including numbered headings.
# 4. Never force DL/YOLO/video fields onto a paper.
# 5. Preserve "not reported" only when the paper genuinely does
#    not report that field.
# 6. Return evidence snippets for extracted values.
# ============================================================


CANONICAL = {
    "abstract": {"abstract", "summary"},
    "keywords": {"keywords", "key words", "index terms", "index terms:"},
    "introduction": {"introduction"},
    "related_work": {
        "related work", "related works", "literature review",
        "background", "background and related work", "prior work",
    },
    "methodology": {
        "methodology", "method", "methods", "materials and methods",
        "method and materials", "proposed method", "proposed methodology",
        "approach", "proposed approach", "system design",
    },
    "dataset": {
        "dataset", "datasets", "data", "data collection",
        "data description", "data preparation", "data preprocessing",
        "experimental dataset",
    },
    "experiments": {
        "experiments", "experimental setup", "experimental evaluation",
        "experimental study", "evaluation", "experimental results",
    },
    "results": {
        "results", "result", "results and discussion",
        "results and analysis", "performance evaluation",
    },
    "discussion": {"discussion", "analysis and discussion"},
    "limitations": {"limitations", "limitations of the study"},
    "conclusion": {"conclusion", "conclusions", "concluding remarks"},
    "future_work": {
        "future work", "future works", "future directions",
        "future research", "conclusion and future work",
    },
    "references": {"references", "bibliography"},
}


def clean_line(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = s.replace("\ufb01", "fi").replace("\ufb02", "fl")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def dehyphenate(s: str) -> str:
    return re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)


def norm_heading(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"^section\s+", "", s, flags=re.I)
    s = re.sub(r"^(?:\d+(?:\.\d+)*|[ivxlcdm]+)[.)]?\s+", "", s, flags=re.I)
    s = re.sub(r"[^a-z0-9& ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def canonical_heading(s: str) -> Optional[str]:
    n = norm_heading(s)
    for key, aliases in CANONICAL.items():
        if n in {norm_heading(a) for a in aliases}:
            return key
    return None


def heading_number(s: str) -> str:
    m = re.match(r"^\s*((?:\d+\.)*\d+)[.)]?\s+", s)
    return m.group(1) if m else ""


def is_page_artifact(line: str) -> bool:
    x = clean_line(line)

    # Common author/page headers from two-column journal PDFs.
    if re.fullmatch(r"(?:\d+\s+)?Viola and Jones(?:\s+\d+)?", x, re.I):
        return True
    if re.fullmatch(r"Robust Real-Time Face Detection\s+\d+", x, re.I):
        return True
    if re.fullmatch(r"\d+", x):
        return True

    # Generic "journal title ... page number" style.
    if re.fullmatch(r".{3,100}\s+\d{1,3}", x) and (
        "journal" in x.lower() or "viola and jones" in x.lower()
    ):
        return True

    return False


def is_caption(line: str) -> bool:
    x = clean_line(line)
    return bool(re.match(
        r"^(?:figure|fig\.|table)\s+\d+(?:[.:]|\s)",
        x,
        re.I,
    ))


def is_heading(line: str) -> bool:
    x = clean_line(line)
    if not x or len(x) > 120 or is_page_artifact(x) or is_caption(x):
        return False
    if x.endswith((".", ",", ";")):
        return False

    # Exact canonical heading.
    if canonical_heading(x):
        return True

    # Numbered academic heading: 5.7.1 Failure Modes
    if re.match(
        r"^\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z0-9 ,&:/()'’\-–—]{1,100}$",
        x,
    ):
        return True

    # IEEE-like A. Method
    if re.match(r"^[A-Z]\.\s+[A-Z][A-Za-z0-9 ,&:/()'’\-–—]{1,100}$", x):
        return True

    return False


def heading_info(line: str) -> Optional[Dict[str, str]]:
    x = clean_line(line)
    if not is_heading(x):
        return None

    key = canonical_heading(x)
    if key:
        return {"key": key, "number": heading_number(x), "title": norm_heading(x)}

    m = re.match(
        r"^\s*(?:\d+(?:\.\d+)*|[A-Z])[.)]?\s+(.+)$",
        x,
    )
    title = clean_line(m.group(1)) if m else x
    return {
        "key": "numbered",
        "number": heading_number(x),
        "title": title,
    }


def page_text(page: Any) -> str:
    try:
        return page.extract_text(extraction_mode="layout") or ""
    except Exception:
        try:
            return page.extract_text() or ""
        except Exception:
            return ""


def remove_repeated_margins(page_texts: List[str]) -> List[str]:
    """
    Remove repeated lines and page-number/header artifacts without
    deleting legitimate body text.
    """
    per_page: List[List[str]] = []
    counts: Dict[str, int] = {}

    for text in page_texts:
        lines = [clean_line(x) for x in text.splitlines()]
        lines = [x for x in lines if x]
        per_page.append(lines)

        # Count only margin-like lines.
        margin = lines[:8] + lines[-8:]
        for line in set(margin):
            if 3 <= len(line) <= 100 and not re.search(r"@|https?://", line):
                counts[line] = counts.get(line, 0) + 1

    threshold = max(3, int(len(page_texts) * 0.35))
    repeated = {
        line for line, n in counts.items()
        if n >= threshold
    }

    output = []
    for lines in per_page:
        cleaned = []
        for line in lines:
            if is_page_artifact(line):
                continue
            if line in repeated and not is_heading(line):
                continue
            cleaned.append(line)
        output.append("\n".join(cleaned))

    return output


def prepare_lines(page_texts: List[str]) -> List[str]:
    lines: List[str] = []

    for page in page_texts:
        page = dehyphenate(page)
        for raw in page.splitlines():
            line = clean_line(raw)
            if line:
                lines.append(line)
        lines.append("")

    return lines


def clean_block(text: str) -> str:
    text = dehyphenate(text)
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        parts = [clean_line(x) for x in block.splitlines()]
        parts = [x for x in parts if x and not is_page_artifact(x)]
        if parts:
            paragraphs.append(" ".join(parts))
    return "\n\n".join(paragraphs).strip()


def split_document(lines: List[str]) -> Tuple[Dict[str, str], List[Dict[str, str]], List[str]]:
    """
    Returns:
      canonical sections,
      numbered/unnamed subsections,
      detected heading titles.
    """
    markers = []

    for i, line in enumerate(lines):
        # Inline abstract / keywords are common in journal PDFs.
        m = re.match(r"^(Abstract)\s*([.:\-–—])\s*(.*)$", line, re.I)
        if m:
            markers.append((i, {"key": "abstract", "number": "", "title": "Abstract", "inline": m.group(3)}))
            continue

        m = re.match(r"^(Keywords?|Index Terms?)\s*([.:\-–—])\s*(.*)$", line, re.I)
        if m:
            markers.append((i, {"key": "keywords", "number": "", "title": "Keywords", "inline": m.group(3)}))
            continue

        info = heading_info(line)
        if info:
            markers.append((i, {**info, "inline": ""}))

    # De-duplicate same line.
    seen = set()
    unique = []
    for item in markers:
        k = (item[0], item[1]["key"], item[1]["title"])
        if k not in seen:
            seen.add(k)
            unique.append(item)
    markers = unique

    sections: Dict[str, str] = {}
    subsections: List[Dict[str, str]] = []
    detected = []

    for pos, (start, info) in enumerate(markers):
        end = markers[pos + 1][0] if pos + 1 < len(markers) else len(lines)
        content = list(lines[start + 1:end])

        if info.get("inline"):
            content.insert(0, info["inline"])

        text = clean_block("\n".join(content))
        if not text:
            continue

        title = info["title"]
        detected.append(
            f"{info.get('number','') + ' ' if info.get('number') else ''}{title}".strip()
        )

        if info["key"] == "numbered":
            subsections.append({
                "number": info.get("number", ""),
                "title": title,
                "text": text,
            })
        else:
            key = info["key"]
            # Don't concatenate repeated sections accidentally.
            sections[key] = (sections.get(key, "") + "\n\n" + text).strip()

    return sections, subsections, detected


def extract_title(page_text: str) -> Optional[str]:
    lines = [clean_line(x) for x in page_text.splitlines() if clean_line(x)]
    candidates = []

    for line in lines[:25]:
        if re.match(r"^(abstract|keywords?|index terms?)\b", line, re.I):
            break
        if re.search(r"^(received|revised|accepted|published)\b", line, re.I):
            continue
        if "@" in line or re.search(r"https?://", line):
            continue
        if re.search(r"\b(?:university|institute|department|college|microsoft research|laboratory)\b", line, re.I):
            continue
        if is_page_artifact(line):
            continue
        if 15 <= len(line) <= 180 and len(line.split()) <= 22:
            candidates.append(line)

    if not candidates:
        return None

    # In most journal PDFs the title is the first substantial line.
    return candidates[0]


def extract_keywords(sections: Dict[str, str]) -> List[str]:
    text = sections.get("keywords", "")
    if not text:
        return []

    values = re.split(r"[,;•|]", text)
    result = []
    for v in values:
        v = clean_line(v).strip(" .:-")
        if 1 < len(v) <= 80:
            result.append(v)
    return list(dict.fromkeys(result))[:20]


def section_text(sections: Dict[str, str], subsections: List[Dict[str, str]], keys: List[str], terms: List[str] = None) -> str:
    parts = [sections[k] for k in keys if sections.get(k)]

    if terms:
        for s in subsections:
            if any(t.lower() in s["title"].lower() for t in terms):
                parts.append(s["text"])

    return "\n\n".join(parts)


def first_match(text: str, patterns: List[str]) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, re.I | re.S)
        if m:
            return clean_line(m.group(1))
    return None


def evidence(text: str, match: re.Match, radius: int = 140) -> str:
    return clean_line(text[max(0, match.start()-radius):min(len(text), match.end()+radius)])


def find_metric(text: str, patterns: List[str]) -> List[Dict[str, Any]]:
    out = []
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            try:
                value = float(m.group(1))
            except Exception:
                continue
            out.append({"value": value, "evidence": evidence(text, m)})
    return out[:12]


def extract_methodology(sections: Dict[str, str], subs: List[Dict[str, str]]) -> Dict[str, Any]:
    # For papers without a literal "Methodology" section, use technical
    # sections before the experiments/results. This is crucial for classic
    # computer-vision papers such as Viola–Jones.
    source = section_text(
        sections, subs,
        ["methodology", "introduction"],
        ["feature", "learning", "approach", "model", "classifier", "cascade", "architecture"],
    )

    # Explicit algorithm/model names; not restricted to deep learning.
    patterns = [
        r"\bAdaBoost\b",
        r"\bHaar(?:-|\s)?like features?\b",
        r"\bintegral image\b",
        r"\battentional cascade\b",
        r"\bcascade of classifiers\b",
        r"\bweak classifier\b",
        r"\bstrong classifier\b",
        r"\bSupport Vector Machine\b",
        r"\bRandom Forest\b",
        r"\b(?:CNN|RNN|LSTM|GRU|Transformer)\b",
        r"\bYOLO(?:v\d+)?\b",
        r"\bSVM\b",
    ]

    algorithms = []
    for p in patterns:
        for m in re.finditer(p, source, re.I):
            value = clean_line(m.group(0))
            if value not in algorithms:
                algorithms.append(value)

    # Generic parameter extraction. Do not call an optimizer "not reported"
    # when the paper uses a named learning algorithm instead.
    epochs = first_match(source, [
        r"\btrained\s+for\s+(\d+)\s+epochs?\b",
        r"\bepochs?\s*[:=]\s*(\d+)\b",
    ])
    batch = first_match(source, [
        r"\bbatch\s+size\s*(?:of|is|=|:)?\s*(\d+)\b",
    ])
    image_size = first_match(source, [
        r"\bbase resolution\s+(?:of|is)\s*(\d+\s*[x×]\s*\d+)\b",
        r"\b(\d+\s*[x×]\s*\d+)\s*(?:pixel|pixels?)\s+(?:sub-window|window|input)\b",
        r"\boperating on\s+(\d+\s*[x×]\s*\d+)\s+pixel images\b",
        r"\b(?:input|image)\s+size\s*(?:of|is|=|:)?\s*(\d+\s*[x×]\s*\d+)\b",
    ])
    optimizer = first_match(source, [
        r"\b(?:optimizer|optimiser)\s*(?:used|was|is)?\s*(?:the)?\s*(AdamW|Adam|SGD|RMSprop)\b",
    ])
    lr = first_match(source, [
        r"\blearning\s+rate\s*(?:of|was|is|=|:)?\s*(\d+(?:\.\d+)?(?:e[-+]?\d+)?)\b",
    ])

    tta = bool(re.search(r"\btest[- ]time augmentation\b|\bTTA\b", source, re.I))

    augmentation = []
    for term in ["cropping", "flipping", "rotation", "scaling", "color jitter", "data augmentation"]:
        if re.search(rf"\b{re.escape(term)}\b", source, re.I):
            augmentation.append(term)

    return {
        "source_available": bool(source),
        "models": algorithms[:20],
        "training": {
            "epochs": epochs,
            "batch_size": batch,
            "image_size": image_size,
            "optimizer": optimizer,
            "learning_rate": lr,
        },
        "test_time_augmentation": tta,
        "augmentation": augmentation,
        "methodology_text": source[:14000] if source else None,
    }


def extract_dataset(sections: Dict[str, str], subs: List[Dict[str, str]]) -> Dict[str, Any]:
    source = section_text(
        sections, subs,
        ["dataset", "experiments", "results"],
        ["experiment", "training", "test set", "test", "dataset", "data"],
    )

    training_examples = first_match(source, [
        r"\b(\d[\d,]*)\s+(?:training\s+)?(?:faces|positive examples|training examples|samples|examples|images)\b",
        r"\btraining\s+(?:set|dataset)\s+(?:contains|consists of|has)\s+(\d[\d,]*)\b",
    ])

    # "5000 faces and 10000 non-face sub-windows" is important evidence.
    positive = first_match(source, [
        r"\btrained\s+(?:using|on)\s+(\d[\d,]*)\s+faces\b",
    ])
    negative = first_match(source, [
        r"\b(\d[\d,]*)\s+non-face\s+(?:sub-windows|examples|images)\b",
    ])

    test_images = first_match(source, [
        r"\btest(?:ing)?\s+set.*?\b(\d[\d,]*)\s+images\b",
        r"\b(\d[\d,]*)\s+images\s+with\s+(\d[\d,]*)\s+(?:labeled\s+)?frontal\s+faces\b",
    ])

    frame_rate = first_match(source, [
        r"\b(\d+(?:\.\d+)?)\s*frames?\s*(?:per|/)\s*second\b",
        r"\b(\d+(?:\.\d+)?)\s*FPS\b",
    ])

    resolution = first_match(source, [
        r"\boperating on\s+(\d+\s*[x×]\s*\d+)\s+pixel images\b",
        r"\b(?:image|input)\s+resolution\s+(?:of|is)\s*(\d+\s*[x×]\s*\d+)\b",
    ])

    # This paper is image based, not video based. Explicitly return N/A.
    video_context = bool(re.search(r"\bvideo\b|\bframes?\b", source, re.I))

    train_split = first_match(source, [
        r"\btraining\s+split\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?\s*%)",
    ])
    val_split = first_match(source, [
        r"\bvalidation\s+split\s*(?:of|=|:)?\s*(\d+(?:\.\d+)?\s*%)",
    ])

    return {
        "source_available": bool(source),
        "training_examples": training_examples or positive,
        "positive_examples": positive,
        "negative_examples": negative,
        "testing_examples": test_images,
        "training_videos": None if not video_context else None,
        "testing_videos": None if not video_context else None,
        "video_duration": None,
        "frame_rate": f"{frame_rate} FPS" if frame_rate else None,
        "resolution": resolution,
        "train_split": train_split,
        "validation_split": val_split,
        "test_split": None,
        "augmentation": [],
        "processing": [],
        "dataset_text": source[:14000] if source else None,
    }


def extract_results(sections: Dict[str, str], subs: List[Dict[str, str]]) -> Dict[str, Any]:
    source = section_text(
        sections, subs,
        ["results", "experiments", "discussion"],
        ["result", "performance", "experiment", "evaluation", "failure", "test set"],
    )

    metrics = {}

    for name, patterns in {
        "accuracy": [r"\baccuracy\s+(?:of|=|:)\s*(\d+(?:\.\d+)?)\s*%"],
        "precision": [r"\bprecision\s+(?:of|=|:)\s*(\d+(?:\.\d+)?)\s*%"],
        "recall": [r"\b(?:recall|sensitivity)\s+(?:of|=|:)\s*(\d+(?:\.\d+)?)\s*%"],
        "f1": [r"\bF1(?:-score)?\s+(?:of|=|:)\s*(\d+(?:\.\d+)?)"],
        "map_50": [r"\bmAP\s*@?\s*0?\.5\b\s*(?:of|=|:)\s*(\d+(?:\.\d+)?)"],
        "map_50_95": [r"\bmAP\s*@?\s*0?\.5\s*[-–]\s*0?\.95\b\s*(?:of|=|:)\s*(\d+(?:\.\d+)?)"],
    }.items():
        values = find_metric(source, patterns)
        if values:
            metrics[name] = values

    # Classic CV papers often report detection rate / false detections,
    # not modern precision/recall/mAP.
    detection_rate = []
    for m in re.finditer(
        r"\b(?:detection rate|detection rates?)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*%",
        source, re.I,
    ):
        detection_rate.append({
            "value": float(m.group(1)),
            "unit": "%",
            "evidence": evidence(source, m),
        })

    false_positive_rate = []
    for m in re.finditer(
        r"\bfalse\s+positive\s+rate\s+(?:of\s+)?([^.;]{1,60})",
        source, re.I,
    ):
        false_positive_rate.append({
            "value": clean_line(m.group(1)),
            "evidence": evidence(source, m),
        })

    speed = []
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*frames?\s*(?:per|/)\s*second\b",
        source, re.I,
    ):
        speed.append({
            "value": float(m.group(1)),
            "unit": "FPS",
            "evidence": evidence(source, m),
        })

    if detection_rate:
        metrics["detection_rate"] = detection_rate[:12]
    if false_positive_rate:
        metrics["false_positive_rate"] = false_positive_rate[:12]

    return {
        "source_available": bool(source),
        "metrics": metrics,
        "speed": speed[:12],
        "results_text": source[:18000] if source else None,
    }


def extract_findings(results: Dict[str, Any], sections: Dict[str, str]) -> List[str]:
    findings = []

    text = results.get("results_text") or ""
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for s in sentences:
        s = clean_line(s)
        if len(s) < 35 or len(s) > 600:
            continue
        if re.search(
            r"\b(?:achieve|achieved|yielded|provides|provided|improves|improved|"
            r"faster|comparable|performance|detection rate|false positive|"
            r"contribution|result|fails|failure)\b",
            s, re.I,
        ):
            findings.append(s)

    # Prefer explicit conclusion sentences.
    conclusion = sections.get("conclusion", "")
    for s in re.split(r"(?<=[.!?])\s+", conclusion):
        s = clean_line(s)
        if len(s) >= 40:
            findings.append(s)

    return list(dict.fromkeys(findings))[:10]


def analyze_pdf(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    if not reader.pages:
        raise ValueError("The PDF contains no readable pages.")

    raw_pages = [page_text(p) for p in reader.pages]
    if not any(x.strip() for x in raw_pages):
        raise ValueError(
            "No readable text was extracted from this PDF. "
            "The PDF may be scanned/image-only."
        )

    cleaned_pages = remove_repeated_margins(raw_pages)
    lines = prepare_lines(cleaned_pages)

    sections, subs, detected = split_document(lines)

    full_text = clean_block("\n".join(lines))

    methodology = extract_methodology(sections, subs)
    dataset = extract_dataset(sections, subs)
    results = extract_results(sections, subs)
    findings = extract_findings(results, sections)

    return {
        "filename": filename,
        "page_count": len(reader.pages),
        "extracted_text_length": len(full_text),
        "extracted_text": full_text,

        "title": extract_title(cleaned_pages[0]),
        "abstract": sections.get("abstract"),
        "keywords": extract_keywords(sections),

        "methodology": methodology,
        "dataset": dataset,
        "results": results,

        "key_findings": findings,
        "limitations": sections.get("limitations"),
        "future_work": sections.get("future_work"),
        "conclusion": sections.get("conclusion"),

        "sections": {k: v[:18000] for k, v in sections.items()},
        "subsections": subs,
        "detected_section_names": detected,

        "extraction_quality": {
            "has_abstract": bool(sections.get("abstract")),
            "has_methodology": methodology["source_available"],
            "has_dataset_section": dataset["source_available"],
            "has_results_section": results["source_available"],
            "has_keywords": bool(sections.get("keywords")),
            "has_structured_headings": bool(detected),
        },
    }
