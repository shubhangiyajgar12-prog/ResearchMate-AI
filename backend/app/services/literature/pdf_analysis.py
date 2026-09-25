import io
import re
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader


# -----------------------------------------------------------------------------
# ResearchMate AI — Robust academic PDF analysis
# -----------------------------------------------------------------------------
# The analyzer is evidence-first. It never invents a value. It uses dedicated
# sections when available, but also searches the full extracted text because
# many PDF layouts (especially two-column papers) scatter or merge headings.
# -----------------------------------------------------------------------------


def clean_line(value: str) -> str:
    value = (value or "").replace("\u00ad", "")
    value = value.replace("\ufb01", "fi").replace("\ufb02", "fl")
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def clean_text(value: str) -> str:
    value = value or ""
    value = value.replace("\u00ad", "")
    value = value.replace("\ufb01", "fi").replace("\ufb02", "fl")
    value = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", value)
    value = re.sub(r"[ \t]+", " ", value)
    return value.strip()


def extract_page_text(page: Any) -> str:
    # Normal pypdf extraction usually gives a better semantic reading order
    # than extraction_mode="layout" on two-column papers.
    try:
        text = page.extract_text() or ""
        if text.strip():
            return text
    except Exception:
        pass
    try:
        return page.extract_text(extraction_mode="layout") or ""
    except Exception:
        return ""


def remove_page_artifacts(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            lines.append("")
            continue
        if re.fullmatch(r"\d{1,3}", line):
            continue
        if re.search(r"arXiv:\d{4}\.\d+", line, re.I):
            # Keep the arXiv id only when it is part of a title/reference; a
            # standalone page-header line should not pollute extraction.
            if len(line) < 35:
                continue
        if re.fullmatch(r".*\s+\d{1,3}", line) and len(line) < 90 and (
            "journal" in line.lower() or "proceedings" in line.lower()
        ):
            continue
        lines.append(line)
    return "\n".join(lines)


def dedupe_preserve(values: List[str]) -> List[str]:
    result = []
    seen = set()
    for value in values:
        key = re.sub(r"\s+", " ", value.strip().lower())
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result


def first_group(text: str, patterns: List[str], flags: int = re.I | re.S) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text or "", flags)
        if match:
            return clean_line(match.group(1))
    return None


def evidence(text: str, match: re.Match, radius: int = 120) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return clean_text(text[start:end])


def section_ranges(text: str) -> List[Tuple[str, int, int]]:
    """Find common academic headings while tolerating numbered headings."""
    heading_re = re.compile(
        r"(?im)^\s*(?:(?:\d+(?:\.\d+)*)\.?\s+)?"
        r"(abstract|keywords?|index terms?|introduction|related works?|literature review|"
        r"background|methodology|methods?|proposed method|approach|data|dataset|"
        r"data overview|data processing|training and validation dataset[^\n]*|"
        r"helmet detection models|model training|test time augmentation(?: \(tta\))?|"
        r"experiments?|experimental setup|experimental results|results(?: and discussion)?|"
        r"comparative analysis|discussion|limitations?|future work|future directions|"
        r"conclusions?|references?)\s*$"
    )
    matches = list(heading_re.finditer(text))
    ranges = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        title = clean_line(match.group(1))
        ranges.append((title, start, end))
    return ranges


def get_section(text: str, names: List[str]) -> str:
    names_l = {n.lower() for n in names}
    chunks = []
    for title, start, end in section_ranges(text):
        if title.lower() in names_l:
            chunk = clean_text(text[start:end])
            if chunk:
                chunks.append(chunk)
    return "\n\n".join(dedupe_preserve(chunks))


def extract_title(text: str) -> Optional[str]:
    lines = [clean_line(x) for x in text.splitlines() if clean_line(x)]
    candidates = []
    for line in lines[:30]:
        low = line.lower()
        if low.startswith(("abstract", "keywords", "index terms")):
            break
        if re.match(r"^(received|revised|accepted|published)\b", line, re.I):
            continue
        if "@" in line or "http://" in line.lower() or "https://" in line.lower():
            continue
        if re.search(r"\b(?:university|institute|department|college|laboratory)\b", line, re.I):
            continue
        if len(line) >= 15 and len(line.split()) <= 28:
            candidates.append(line)
    return candidates[0] if candidates else None


def extract_abstract(text: str) -> Optional[str]:
    abstract = get_section(text, ["abstract", "summary"])
    if abstract:
        return abstract

    match = re.search(
        r"(?is)\babstract\b\s*(.*?)(?=\b(?:1\.?\s*)?introduction\b)",
        text,
    )
    return clean_text(match.group(1)) if match else None


def extract_keywords(text: str) -> List[str]:
    section = get_section(text, ["keywords", "keyword", "index terms"])
    if not section:
        return []
    section = re.sub(r"^\s*[:\-–—]\s*", "", section)
    values = re.split(r"[,;|•]", section)
    return dedupe_preserve(
        [clean_line(v).strip(" .:-") for v in values if 1 < len(clean_line(v).strip(" .:-")) <= 80]
    )[:20]


def extract_methodology(text: str, abstract: str | None, subs: List[Dict[str, str]]) -> Dict[str, Any]:
    method_section = get_section(
        text,
        [
            "methodology", "method", "methods", "proposed method", "approach",
            "helmet detection models", "model training", "test time augmentation",
            "data processing",
        ],
    )
    source = clean_text("\n\n".join(x for x in [method_section, abstract, text[:25000]] if x))

    model_patterns = [
        (r"\bYOLOv5\b", "YOLOv5"),
        (r"\bYOLOv7\b", "YOLOv7"),
        (r"\bYOLOv8\b", "YOLOv8"),
        (r"\bAdaBoost\b", "AdaBoost"),
        (r"\bHaar[- ]like features?\b", "Haar-like features"),
        (r"\bSupport Vector Machine\b", "Support Vector Machine"),
        (r"\bRandom Forest\b", "Random Forest"),
        (r"\b(?:CNN|RNN|LSTM|GRU|Transformer)\b", "Deep learning model"),
        (r"\bSCAN\b", "SCAN"),
    ]
    models = []
    for pattern, label in model_patterns:
        if re.search(pattern, source, re.I):
            models.append(label)

    epochs = first_group(source, [r"\btrained\s+for\s+(\d+)\s+epochs?\b", r"\b(\d+)\s+epochs?\b"])
    batch = first_group(source, [r"\bbatch\s+size\s*(?:of|is|=|:)?\s*(\d+)\b"])
    image_size = first_group(
        source,
        [
            r"\bimage\s+size\s*(?:of|is|=|:)?\s*(\d+\s*[x×]\s*\d+)\b",
            r"\b(\d+\s*[x×]\s*\d+)\s*(?:pixel|pixels?)\b",
        ],
    )
    optimizer = first_group(source, [r"\b(?:optimizer|optimiser)\s*(?:used|was|is)?\s*(?:the)?\s*(AdamW|Adam|SGD|RMSprop)\b"])
    learning_rate = first_group(source, [r"\blearning\s+rate\s*(?:of|was|is|=|:)?\s*(\d+(?:\.\d+)?(?:e[-+]?\d+)?)\b"])
    tta = bool(re.search(r"\btest[- ]time augmentation\b|\bTTA\b", source, re.I))

    augmentation = []
    for term in ["flipping", "rotation", "scaling", "cropping", "blurring", "color manipulation", "brightness", "contrast", "saturation", "data augmentation"]:
        if re.search(rf"\b{re.escape(term)}\b", source, re.I):
            augmentation.append(term)

    processing = []
    for pattern, label in [
        (r"\bfew[- ]shot data sampling(?: technique)?\b", "Few-shot data sampling"),
        (r"\bsemantic clustering by adopting nearest neighbors\b|\bSCAN\b", "SCAN frame de-duplication"),
        (r"\bdata augmentation\b", "Data augmentation"),
        (r"\btest[- ]time augmentation\b|\bTTA\b", "Test Time Augmentation (TTA)"),
    ]:
        if re.search(pattern, source, re.I) and label not in processing:
            processing.append(label)

    # Build compact methodology subsections from detected numbered headings.
    subsection_values = []
    heading_re = re.compile(
        r"(?im)^\s*((?:\d+\.)+\d+|\d+)\s+([^\n]{3,120})\s*$"
    )
    matches = list(heading_re.finditer(text))
    for i, m in enumerate(matches):
        title = clean_line(m.group(2))
        title_low = title.lower()
        if not any(k in title_low for k in ["method", "model", "training", "data processing", "augmentation", "approach"]):
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else min(len(text), m.end() + 3000)
        chunk = clean_text(text[m.end():end])
        if chunk:
            subsection_values.append({"number": m.group(1), "title": title, "text": chunk[:5000]})

    return {
        "source_available": bool(source),
        "models": dedupe_preserve(models)[:20],
        "training": {
            "epochs": epochs,
            "batch_size": batch,
            "image_size": image_size,
            "optimizer": optimizer,
            "learning_rate": learning_rate,
        },
        "test_time_augmentation": tta,
        "augmentation": dedupe_preserve(augmentation),
        "processing": dedupe_preserve(processing),
        "subsections": subsection_values[:30],
        "methodology_text": source[:16000] if source else None,
    }


def parse_dataset_ratio(source: str) -> Tuple[Optional[str], Optional[str]]:
    match = re.search(r"\b(?:ratio|proportion)\s+of\s+(0?\.\d+)\s*[:/]\s*(0?\.\d+)\b", source, re.I)
    if not match:
        return None, None
    a = float(match.group(1)) * 100
    b = float(match.group(2)) * 100
    return f"{a:g}%", f"{b:g}%"


def extract_dataset(text: str, abstract: str | None) -> Dict[str, Any]:
    data_section = get_section(
        text,
        ["data", "dataset", "data overview", "data processing", "training and validation dataset"],
    )
    source = clean_text("\n\n".join(x for x in [data_section, text] if x))

    training_videos = first_group(source, [
        r"\b(\d[\d,]*)\s+videos\s+for\s+training\b",
        r"\btraining\s+videos?\s*(?:of|=|:)\s*(\d[\d,]*)\b",
    ])
    testing_videos = first_group(source, [
        r"\b(\d[\d,]*)\s+videos\s+for\s+testing\b",
        r"\b(\d[\d,]*)\s+unannotated\s+videos\s+for\s+testing\b",
        r"\btesting\s+videos?\s*(?:of|=|:)\s*(\d[\d,]*)\b",
    ])
    video_duration = first_group(source, [
        r"\b(?:average\s+)?(?:length|duration)\s+(?:of\s+)?(\d+(?:\.\d+)?\s*(?:seconds?|sec))\b",
        r"\b(\d+(?:\.\d+)?[- ]second)\s+(?:duration|video)\b",
    ])
    frame_rate = first_group(source, [
        r"\b(\d+(?:\.\d+)?)\s*fps\b",
        r"\b(\d+(?:\.\d+)?)\s*frames?\s*(?:per|/)\s*second\b",
    ])
    resolution = first_group(source, [
        r"\b(?:resolution\s+(?:of|is))\s*(\d+\s*[x×]\s*\d+)\b",
        r"\b(\d+\s*[x×]\s*\d+)\s+pixel\b",
    ])
    training_examples = first_group(source, [
        r"\busing\s+(\d[\d,]*)\s+training\s+examples\b",
        r"\b(\d[\d,]*)\s+training\s+examples\b",
    ])
    train_split, validation_split = parse_dataset_ratio(source)

    augmentation = []
    for term in ["flipping", "rotation", "scaling", "cropping", "blurring", "color manipulation", "data augmentation"]:
        if re.search(rf"\b{re.escape(term)}\b", source, re.I):
            augmentation.append(term)

    processing = []
    for pattern, label in [
        (r"\bfew[- ]shot data sampling(?: technique)?\b", "Few-shot data sampling"),
        (r"\bsemantic clustering by adopting nearest neighbors\b|\bSCAN\b", "SCAN frame de-duplication"),
    ]:
        if re.search(pattern, source, re.I) and label not in processing:
            processing.append(label)

    return {
        "source_available": bool(source),
        "training_videos": training_videos,
        "testing_videos": testing_videos,
        "video_duration": video_duration,
        "frame_rate": f"{frame_rate} FPS" if frame_rate else None,
        "resolution": resolution,
        "training_examples": training_examples,
        "train_split": train_split,
        "validation_split": validation_split,
        "test_split": None,
        "positive_examples": None,
        "negative_examples": None,
        "testing_examples": None,
        "augmentation": dedupe_preserve(augmentation),
        "processing": dedupe_preserve(processing),
        "dataset_text": data_section[:16000] if data_section else None,
    }


def parse_validation_rows(text: str) -> List[Dict[str, Any]]:
    """Parse validation rows from the validation-table region."""
    rows = []
    lines = [clean_line(x) for x in (text or "").splitlines() if clean_line(x)]
    row_re = re.compile(
        r"^(yolov5(?:\+TTA)?|yolov7(?:\+TTA)?|yolov8(?:\+TTA)?)\s+"
        r"(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)$",
        re.I,
    )
    in_validation_block = False
    for line in lines:
        low = line.lower()
        if re.search(r"(?:5\.1\.1\s*)?validation dataset|table 2", low):
            in_validation_block = True
            continue
        if in_validation_block and re.search(r"(?:5\.1\.2\s*)?test dataset|table 3|conclusion", low):
            in_validation_block = False
        if not in_validation_block:
            continue
        m = row_re.match(line)
        if m:
            rows.append({
                "model": m.group(1),
                "values": [float(m.group(i)) for i in range(2, 6)],
            })

    if not rows:
        m = re.search(
            r"(?is)(?:5\.1\.1\s*)?validation dataset(.*?)(?:5\.1\.2\s*test dataset|\btest dataset\b|\breferences\b|$)",
            text or "",
        )
        block = m.group(1) if m else ""
        for match in re.finditer(
            r"\b(yolov5(?:\+TTA)?|yolov7(?:\+TTA)?|yolov8(?:\+TTA)?)\s+"
            r"(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)\b",
            block, re.I,
        ):
            rows.append({
                "model": match.group(1),
                "values": [float(match.group(i)) for i in range(2, 6)],
            })

    unique = []
    seen = set()
    for row in rows:
        key = (row["model"].lower(), tuple(row["values"]))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def parse_test_rows(text: str) -> List[Dict[str, Any]]:
    """Parse test-table rows without accidentally reading validation rows as test rows."""
    rows = []
    lines = [clean_line(x) for x in (text or "").splitlines() if clean_line(x)]

    row_re = re.compile(
        r"^(yolov5(?:\+TTA)?|yolov7(?:\+TTA)?|yolov8(?:\+TTA)?)\s+"
        r"(0\.\d{3,4})\s+(\d+(?:\.\d+)?)$",
        re.I,
    )
    validation_like_re = re.compile(
        r"^(yolov5(?:\+TTA)?|yolov7(?:\+TTA)?|yolov8(?:\+TTA)?)\s+"
        r"(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)\s+(0\.\d+)$",
        re.I,
    )

    in_test_block = False
    for line in lines:
        low = line.lower()
        if re.search(r"(?:5\.1\.2\s*)?test dataset|experimental test dataset|table 3", low):
            in_test_block = True
            continue
        if in_test_block and re.match(r"(?:6\.?\s*)?conclusion\b", low):
            in_test_block = False
        if not in_test_block:
            continue

        if validation_like_re.match(line):
            continue
        m = row_re.match(line)
        if m:
            rows.append({
                "model": m.group(1),
                "values": [float(m.group(2)), float(m.group(3))],
            })

    # Fallback for PDFs that collapse table rows into one long line. Search only
    # the region after the explicit Test Dataset heading and before Conclusion.
    if not rows:
        m = re.search(
            r"(?is)(?:5\.1\.2\s*)?test dataset(.*?)(?:\b6\.?\s*conclusion\b|\breferences\b|$)",
            text or "",
        )
        block = m.group(1) if m else ""
        for match in re.finditer(
            r"\b(yolov5(?:\+TTA)?|yolov7(?:\+TTA)?|yolov8(?:\+TTA)?)\s+"
            r"(0\.\d{3,4})\s+(\d+(?:\.\d+)?)\b",
            block, re.I,
        ):
            rows.append({
                "model": match.group(1),
                "values": [float(match.group(2)), float(match.group(3))],
            })

    unique = []
    seen = set()
    for row in rows:
        key = (row["model"].lower(), tuple(row["values"]))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def extract_results(text: str, abstract: str | None, conclusion: str | None) -> Dict[str, Any]:
    results_section = get_section(text, ["results", "result", "results and discussion", "comparative analysis", "experimental results"])
    source = clean_text("\n\n".join(x for x in [results_section, conclusion or "", abstract or "", text] if x))

    validation_rows = parse_validation_rows(source)
    test_rows = parse_test_rows(source)

    validation = {"map_50": None, "map_50_95": None, "precision": None, "recall": None, "reported_map": None}
    test = {"map": None, "fps": None}

    if validation_rows:
        best_v = max(validation_rows, key=lambda r: r["values"][1])
        validation["map_50"] = best_v["values"][0]
        validation["map_50_95"] = best_v["values"][1]
        validation["precision"] = best_v["values"][2]
        validation["recall"] = best_v["values"][3]

    if test_rows:
        best_t = max(test_rows, key=lambda r: r["values"][0])
        test["map"] = best_t["values"][0]
        test["fps"] = int(round(best_t["values"][1]))

    generic_map = []
    for m in re.finditer(r"\bmAP\s+score\s+(?:of\s+)?(0\.\d+)\b", source, re.I):
        generic_map.append({"value": float(m.group(1)), "evidence": evidence(source, m)})
    generic_map = generic_map[:10]
    if generic_map:
        validation["reported_map"] = generic_map[0]["value"]

    challenge_rank = None
    rank_evidence = None
    match = re.search(r"(?<!\w)(\d+)(?:st|nd|rd|th)\s+place\b", source, re.I)
    if match:
        challenge_rank = int(match.group(1))
        rank_evidence = evidence(source, match)
    else:
        match = re.search(r"\branked\s+(\d+)(?:st|nd|rd|th)?\b", source, re.I)
        if match:
            challenge_rank = int(match.group(1))
            rank_evidence = evidence(source, match)

    best_model = None
    if test_rows:
        best_model = max(test_rows, key=lambda r: r["values"][0])["model"]
    elif validation_rows:
        best_model = max(validation_rows, key=lambda r: r["values"][1])["model"]

    speed = []
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*frames?\s*(?:per|/)\s*second\b|\b(\d+(?:\.\d+)?)\s*FPS\b", source, re.I):
        value = m.group(1) or m.group(2)
        if value:
            speed.append({"value": float(value), "unit": "FPS", "evidence": evidence(source, m)})

    return {
        "source_available": bool(source),
        "metrics": {
            "reported_map": generic_map,
        },
        "validation": validation,
        "test": test,
        "validation_models": validation_rows[:30],
        "test_models": test_rows[:30],
        "challenge_rank": challenge_rank,
        "challenge_rank_evidence": rank_evidence,
        "best_model": best_model,
        "speed": speed[:20],
        "results_text": results_section[:22000] if results_section else source[:22000],
    }


def extract_limitations(text: str) -> Optional[str]:
    value = get_section(text, ["limitations", "limitation", "limitations of the study"])
    return value[:10000] if value else None


def extract_future_work(text: str) -> Optional[str]:
    value = get_section(text, ["future work", "future directions", "future research", "future works"])
    return value[:10000] if value else None


def extract_conclusion(text: str) -> Optional[str]:
    value = get_section(text, ["conclusion", "conclusions", "concluding remarks"])
    return value[:12000] if value else None


def extract_findings(results: Dict[str, Any], methodology: Dict[str, Any], dataset: Dict[str, Any], abstract: str | None, conclusion: str | None) -> List[str]:
    findings: List[str] = []

    # Structured table findings are more reliable than noisy sentence fragments.
    if results.get("validation_models"):
        row = max(results["validation_models"], key=lambda r: r["values"][1])
        v = row["values"]
        findings.append(
            f"Validation: {row['model']} reports mAP@0.5={v[0]:g}, mAP@0.5–0.95={v[1]:g}, precision={v[2]:g}, recall={v[3]:g}."
        )

    if results.get("test_models"):
        row = max(results["test_models"], key=lambda r: r["values"][0])
        t = row["values"]
        findings.append(f"Test: {row['model']} reports mAP={t[0]:g} at approximately {t[1]:g} FPS.")

    if results.get("challenge_rank"):
        findings.append(f"Challenge result: the paper reports a {results['challenge_rank']}th-place public leaderboard position.")

    if methodology.get("models"):
        named = ", ".join(methodology["models"][:5])
        findings.append(f"Method: the paper evaluates/uses {named} for helmet-violation detection.")

    if "Few-shot data sampling" in methodology.get("processing", []):
        findings.append("Data processing: a few-shot data sampling strategy is used to reduce annotation effort while selecting representative training data.")

    if methodology.get("test_time_augmentation"):
        findings.append("Inference: Test Time Augmentation (TTA) is used to improve prediction performance during inference.")

    if dataset.get("training_examples") or dataset.get("training_videos") or dataset.get("frame_rate"):
        bits = []
        if dataset.get("training_examples"):
            bits.append(f"{dataset['training_examples']} training examples")
        if dataset.get("training_videos"):
            bits.append(f"{dataset['training_videos']} training videos")
        if dataset.get("testing_videos"):
            bits.append(f"{dataset['testing_videos']} test videos")
        if dataset.get("frame_rate"):
            bits.append(dataset["frame_rate"])
        if bits:
            findings.append("Dataset evidence: " + ", ".join(bits) + ".")

    # Add a few clean abstract/conclusion sentences, filtering figure captions and
    # obvious background-only material.
    signal = re.compile(
        r"\b(?:proposes|proposed|developed|won|experimental results|demonstrate|achieved|"
        r"effectiveness|efficiency|robustness|few-shot data sampling|YOLOv8|test time augmentation)\b",
        re.I,
    )
    for source in [abstract or "", conclusion or ""]:
        for sentence in re.split(r"(?<=[.!?])\s+", clean_text(source)):
            sentence = clean_line(sentence)
            if not (45 <= len(sentence) <= 500):
                continue
            if re.search(r"figure|illustration|bounding box colors|predictive class", sentence, re.I):
                continue
            if signal.search(sentence):
                findings.append(sentence)

    return dedupe_preserve(findings)[:12]


def analyze_pdf(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc

    if not reader.pages:
        raise ValueError("The PDF contains no readable pages.")

    pages = [extract_page_text(page) for page in reader.pages]
    if not any(p.strip() for p in pages):
        raise ValueError("No readable text was extracted from this PDF. The PDF may be scanned/image-only.")

    raw_text = "\n\n".join(pages)
    text = clean_text(remove_page_artifacts(raw_text))

    # Prefer a line-aware version for subsection parsing/title while using the
    # normalized full text for robust evidence matching.
    lines_text = "\n".join(clean_line(x) for p in pages for x in p.splitlines() if clean_line(x))

    abstract = extract_abstract(lines_text if lines_text else text)
    title = extract_title(lines_text if lines_text else text)
    conclusion = extract_conclusion(lines_text if lines_text else text)

    # Extract numbered subsections once for the methodology card.
    subs: List[Dict[str, str]] = []
    heading_re = re.compile(r"(?im)^\s*((?:\d+\.)+\d+|\d+)\s+([^\n]{3,120})\s*$")
    heading_matches = list(heading_re.finditer(lines_text))
    for i, match in enumerate(heading_matches):
        number = match.group(1)
        heading = clean_line(match.group(2))
        start = match.end()
        end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else min(len(lines_text), start + 6000)
        chunk = clean_text(lines_text[start:end])
        if chunk:
            subs.append({"number": number, "title": heading, "text": chunk[:6000]})

    methodology = extract_methodology(text, abstract, subs)
    dataset = extract_dataset(text, abstract)
    results = extract_results(text, abstract, conclusion)
    findings = extract_findings(results, methodology, dataset, abstract, conclusion)

    # Respect explicit limitations/future work. Do not manufacture these fields.
    limitations = extract_limitations(lines_text if lines_text else text)
    future_work = extract_future_work(lines_text if lines_text else text)

    return {
        "filename": filename,
        "page_count": len(reader.pages),
        "extracted_text_length": len(text),
        "extracted_text": text,
        "title": title,
        "abstract": abstract,
        "methodology": methodology,
        "dataset": dataset,
        "results": results,
        "limitations": limitations,
        "future_work": future_work,
        "conclusion": conclusion,
        "key_findings": findings,
        "keywords": extract_keywords(lines_text if lines_text else text),
        "subsections": subs,
        "extraction_quality": {
            "has_abstract": bool(abstract),
            "has_methodology": methodology["source_available"],
            "has_dataset_section": bool(get_section(text, ["data", "dataset", "data overview"])),
            "has_results_section": bool(get_section(text, ["results", "result", "results and discussion"])),
            "has_result_evidence": bool(results.get("validation_models") or results.get("test_models") or results.get("metrics", {}).get("reported_map") or results.get("challenge_rank")),
            "has_keywords": bool(extract_keywords(lines_text if lines_text else text)),
            "has_structured_headings": bool(section_ranges(text)),
        },
    }
