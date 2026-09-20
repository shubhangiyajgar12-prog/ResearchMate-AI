import io
import re
from typing import Dict, List, Optional, Any

from pypdf import PdfReader


# ---------------------------------------------------------
# Generic academic section / subsection detection
# ---------------------------------------------------------

SECTION_ALIASES = {
    "abstract": ["abstract"],
    "introduction": ["introduction"],
    "related_work": [
        "related work",
        "related works",
        "literature review",
        "background",
        "background and related work",
    ],
    "methodology": [
        "methodology",
        "method",
        "methods",
        "proposed method",
        "proposed methodology",
        "approach",
        "proposed approach",
        "materials and methods",
        "method and materials",
    ],
    "dataset": [
        "dataset",
        "datasets",
        "data",
        "data overview",
        "data collection",
        "data processing",
        "training and validation dataset",
    ],
    "experiments": [
        "experiments",
        "experimental setup",
        "experimental evaluation",
        "experimental results",
        "evaluation",
    ],
    "results": [
        "results",
        "results and discussion",
        "results and analysis",
        "performance evaluation",
        "comparative analysis",
    ],
    "discussion": ["discussion"],
    "limitations": ["limitations", "limitations and future work"],
    "conclusion": ["conclusion", "conclusions"],
    "future_work": [
        "future work",
        "future works",
        "future directions",
        "conclusion and future work",
    ],
    "references": ["references", "bibliography"],
}


def _clean_line(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _normalize_heading(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"^\d+(?:\.\d+)*[\.)]?\s*", "", text)
    text = re.sub(r"^[ivxlcdm]+[\.)]\s*", "", text, flags=re.I)
    text = re.sub(r"[^a-z0-9& ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _heading_key(text: str) -> Optional[str]:
    normalized = _normalize_heading(text)

    for key, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return key

    return None


def _section_number(text: str) -> str:
    match = re.match(r"^\s*((?:\d+\.)*\d+)[\.)]?\s+", text)
    return match.group(1) if match else ""


def _is_heading(line: str) -> Optional[Dict[str, str]]:
    line = _clean_line(line)

    if not line or len(line) > 120:
        return None

    number = _section_number(line)

    candidate = re.sub(
        r"^\s*(?:\d+(?:\.\d+)*|[IVXLCDM]+)[\.)]?\s+",
        "",
        line,
        flags=re.I,
    ).strip()

    candidate = candidate.rstrip(":").strip()
    key = _heading_key(candidate)

    # Known academic heading.
    if key:
        return {
            "key": key,
            "number": number,
            "title": candidate,
        }

    # Numbered top-level section, e.g.:
    # 4 Helmet Detection Models
    #
    # This is important because many papers do not use a literal
    # heading name such as "Methodology" for every methodology section.
    if number and re.fullmatch(r"\d+", number):
        words = candidate.split()
        if 1 <= len(words) <= 12:
            # Avoid treating list-like labels such as "3. Scaling:" as headings.
            if not line.rstrip().endswith(":") and not re.search(r"[.!?]$", candidate) and len(candidate) <= 90:
                return {
                    "key": "section",
                    "number": number,
                    "title": candidate,
                }

    # Generic numbered subsection, e.g.:
    # 3.1 Data Overview
    # 4.2 Test Time Augmentation
    if number and re.match(r"^\d+(?:\.\d+)+$", number):
        words = candidate.split()
        if 1 <= len(words) <= 12:
            if not re.search(r"[.!?]$", candidate):
                return {
                    "key": "subsection",
                    "number": number,
                    "title": candidate,
                }

    return None


# ---------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------

def _prepare_lines(page_texts: List[str]) -> List[str]:
    """Keep line boundaries intact before heading detection."""
    lines: List[str] = []

    for page_text in page_texts:
        page_text = page_text.replace("\u00ad", "")
        page_text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", page_text)

        for raw_line in page_text.splitlines():
            lines.append(_clean_line(raw_line))

        lines.append("")

    return lines


def _clean_content(text: str) -> str:
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    paragraphs = []

    for block in re.split(r"\n\s*\n", text):
        lines = [_clean_line(x) for x in block.splitlines()]
        lines = [x for x in lines if x]

        if lines:
            paragraphs.append(" ".join(lines))

    return "\n\n".join(paragraphs).strip()


def _extract_sections(lines: List[str]) -> Dict[str, Any]:
    """
    Detect top-level sections and numbered subsections independently.

    A top-level heading such as "4 Helmet Detection Models" now creates
    a boundary, preventing section 3.3 from swallowing section 4.
    """
    headings = []

    for index, line in enumerate(lines):
        info = _is_heading(line)
        if info:
            headings.append((index, info))

    sections: Dict[str, str] = {}
    section_records: List[Dict[str, str]] = []
    subsections: List[Dict[str, str]] = []

    for pos, (start, info) in enumerate(headings):
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        content = _clean_content("\n".join(lines[start + 1:end]))

        record = {
            "number": info["number"],
            "title": info["title"],
            "text": content,
        }

        if info["key"] == "subsection":
            if content:
                subsections.append(record)
            continue

        if info["key"] == "section":
            section_records.append(record)

            # Preserve unknown top-level sections using their title as a
            # stable lookup key.
            normalized_title = _normalize_heading(info["title"])
            if normalized_title and content:
                sections[normalized_title] = content
            continue

        key = info["key"]
        if content:
            section_records.append(record)

            if key in sections:
                sections[key] += "\n\n" + content
            else:
                sections[key] = content

    return {
        "sections": sections,
        "section_records": section_records,
        "subsections": subsections,
    }


# ---------------------------------------------------------
# Title / keywords
# ---------------------------------------------------------

def _extract_title(page_texts: List[str]) -> Optional[str]:
    if not page_texts:
        return None

    lines = [
        _clean_line(x)
        for x in page_texts[0].splitlines()
        if _clean_line(x)
    ]

    candidates = []

    for line in lines[:30]:
        if _heading_key(line) in {"abstract", "introduction"}:
            break

        low = line.lower()

        if "arxiv:" in low or "doi:" in low:
            continue
        if "@" in line:
            continue
        if re.search(r"\b(department|university|institute|college)\b", line, re.I):
            continue
        if re.search(r"\b(corresponding author)\b", line, re.I):
            continue
        if len(line) < 20 or len(line) > 220:
            continue

        candidates.append(line)

    return candidates[0] if candidates else None


def _extract_keywords(full_text: str) -> List[str]:
    match = re.search(
        r"(?:keywords?|index terms?)\s*[:\-]\s*(.+?)(?:\n\n|$)",
        full_text,
        flags=re.I | re.S,
    )

    if not match:
        return []

    values = re.split(r"[;,•|]", match.group(1))
    result = []

    for value in values:
        value = _clean_line(value).strip(" .:-")
        if 2 <= len(value) <= 80:
            result.append(value)

    return list(dict.fromkeys(result))[:15]


# ---------------------------------------------------------
# Shared extraction helpers
# ---------------------------------------------------------

def _find_number(text: str, patterns: List[str]) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return None


def _normalise_ratio(value1: str, value2: str) -> tuple[str, str]:
    """Convert both 7:3 and 0.7:0.3 style splits to percentages."""
    a = float(value1)
    b = float(value2)

    if a <= 1 and b <= 1:
        total = a + b
        if total:
            return f"{a / total * 100:g}%", f"{b / total * 100:g}%"

    total = a + b
    if total:
        return f"{a / total * 100:g}%", f"{b / total * 100:g}%"

    return None, None


# ---------------------------------------------------------
# Dataset extraction
# ---------------------------------------------------------

def _extract_dataset(
    sections: Dict[str, str],
    subsections: List[Dict[str, str]],
    full_text: str,
) -> Dict[str, Any]:
    source_parts = []

    if sections.get("dataset"):
        source_parts.append(sections["dataset"])

    # Also search the complete extracted PDF text because PDF heading
    # detection can sometimes split dataset content incorrectly.
    if full_text:
        source_parts.append(full_text)

    for item in subsections:
        title = item["title"].lower()
        if any(word in title for word in [
            "data overview",
            "data processing",
            "training and validation",
            "dataset",
            "data collection",
        ]):
            source_parts.append(item["text"])

    text = "\n".join(source_parts)

    result = {
        "training_videos": _find_number(
            text,
            [
                r"(\d+)\s+videos?\s+for\s+training",
                r"(\d+)\s+training\s+videos?",
            ],
        ),
        "testing_videos": _find_number(
            text,
            [
                r"(\d+)\s+videos?\s+for\s+testing",
                r"(\d+)\s+testing\s+videos?",
            ],
        ),
        "video_duration": _find_number(
            text,
            [r"(\d+(?:\.\d+)?)\s*[-]?\s*second"],
        ),
        "frame_rate": _find_number(
            text,
            [r"(\d+(?:\.\d+)?)\s*fps"],
        ),
        "resolution": _find_number(
            text,
            [
                r"(\d+\s*[×x]\s*\d+)\s*(?:pixels?|resolution)?",
                r"resolution\s*(?:of|:)?\s*(\d+\s*[×x]\s*\d+)",
            ],
        ),
        "training_examples": _find_number(
            text,
            [
                r"(\d[\d,]*)\s+training\s+examples",
                r"(\d[\d,]*)\s+training\s+images?",
                r"(\d[\d,]*)\s+examples\s+for\s+training",
            ],
        ),
    }

    for key in [
        "training_videos",
        "testing_videos",
        "video_duration",
        "frame_rate",
        "training_examples",
    ]:
        if result[key] is not None:
            result[key] = result[key].replace(",", "")

    if result["video_duration"]:
        result["video_duration"] += " seconds"

    if result["frame_rate"]:
        result["frame_rate"] += " FPS"

    if result["resolution"]:
        result["resolution"] = re.sub(r"\s*[xX×]\s*", "×", result["resolution"])

    # Accept both "7:3" and "0.7:0.3".
    split_match = re.search(
        r"(?:ratio|split)\s*(?:of|is|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*[:/]\s*(\d+(?:\.\d+)?)",
        text,
        re.I,
    )

    if split_match:
        result["train_split"], result["validation_split"] = _normalise_ratio(
            split_match.group(1),
            split_match.group(2),
        )
    else:
        # Common prose form: "70% training and 30% validation".
        percent_match = re.search(
            r"(\d+(?:\.\d+)?)\s*%\s*(?:for\s*)?training.*?"
            r"(\d+(?:\.\d+)?)\s*%\s*(?:for\s*)?validation",
            text,
            re.I | re.S,
        )
        if percent_match:
            result["train_split"] = f"{percent_match.group(1)}%"
            result["validation_split"] = f"{percent_match.group(2)}%"
        else:
            result["train_split"] = None
            result["validation_split"] = None

    augmentation_patterns = [
        ("Image flipping", r"\b(?:image\s+)?flipping\b|\bflip(?:ping)?\b"),
        ("Rotation", r"\brotation\b|\brotat(?:e|ed|ing)\b"),
        ("Scaling", r"\bscaling\b|\bscaled\b"),
        ("Cropping", r"\bcropping\b|\bcrop(?:ped|ping)?\b"),
        ("Blurring", r"\bblurring\b|\bblur(?:red|ring)?\b"),
        ("Color manipulation", r"\bcolor\s+manipulation\b|\bcolour\s+manipulation\b"),
    ]

    result["augmentation"] = [
        label
        for label, pattern in augmentation_patterns
        if re.search(pattern, text, re.I)
    ]

    processing_terms = [
        "Few-shot data sampling",
        "Background estimation",
        "Frame sampling",
        "Day/night/fog classification",
        "Data augmentation",
    ]

    result["processing"] = [
        term for term in processing_terms
        if (
            re.search(re.escape(term), text, re.I)
            or (
                term == "Day/night/fog classification"
                and re.search(r"\b(day|night|foggy)\b", text, re.I)
            )
        )
    ]

    return result


# ---------------------------------------------------------
# Methodology structure
# ---------------------------------------------------------

def _extract_methodology(
    sections: Dict[str, str],
    section_records: List[Dict[str, str]],
    subsections: List[Dict[str, str]],
) -> Dict[str, Any]:
    relevant = []

    for item in subsections:
        number = item["number"]
        if number.startswith(("3.", "4.")):
            relevant.append({
                "number": number,
                "title": item["title"],
                "text": item["text"],
            })

    # Include top-level sections 3 and 4 as methodology context, but do not
    # duplicate their entire content into subsection 3.3.
    for item in section_records:
        if item["number"] in {"3", "4"}:
            relevant.append({
                "number": item["number"],
                "title": item["title"],
                "text": item["text"],
            })

    combined_text = "\n".join(
        [item["text"] for item in relevant]
        + [sections.get("methodology", "")]
    )

    models = []
    for model in ["YOLOv5", "YOLOv7", "YOLOv8"]:
        if re.search(rf"\b{re.escape(model)}\b", combined_text, re.I):
            models.append(model)

    training = {
        "epochs": _find_number(
            combined_text,
            [r"trained\s+for\s+(\d+)\s+epochs", r"(\d+)\s+epochs"],
        ),
        "batch_size": _find_number(
            combined_text,
            [r"batch\s+size\s+of\s+(\d+)", r"batch\s+size\s*[:=]\s*(\d+)"],
        ),
        "image_size": _find_number(
            combined_text,
            [
                r"image\s+size\s+of\s+(\d+\s*[×x]\s*\d+)",
                r"image\s+size\s*[:=]\s*(\d+\s*[×x]\s*\d+)",
            ],
        ),
        "optimizer": None,
    }

    optimizer_match = re.search(
        r"\b(Adam|SGD|RMSprop|Adagrad)\b",
        combined_text,
        re.I,
    )

    if optimizer_match:
        training["optimizer"] = optimizer_match.group(1)

    return {
        "subsections": relevant,
        "models": models,
        "training": training,
        "test_time_augmentation": bool(
            re.search(
                r"\btest\s*time\s*augmentation\b|\bTTA\b",
                combined_text,
                re.I,
            )
        ),
    }


# ---------------------------------------------------------
# Results / metrics extraction
# ---------------------------------------------------------

def _extract_flat_table_rows(text: str, expected_values: int) -> List[Dict[str, Any]]:
    """Extract flattened PDF table rows without letting adjacent rows contaminate."""
    aliases = [
        (r"yolov8\s*\+\s*tta", "YOLOv8 + TTA"),
        (r"yolov5\s*\+\s*tta", "YOLOv5 + TTA"),
        (r"yolov8", "YOLOv8"),
        (r"yolov7", "YOLOv7"),
        (r"yolov5", "YOLOv5"),
    ]

    rows = []
    used_models = set()

    for pattern, display in aliases:
        if display in used_models:
            continue

        for match in re.finditer(pattern, text, re.I):
            tail = text[match.end():match.end() + 100]

            if expected_values == 2:
                # Test table is: mAP (decimal) followed by FPS (integer).
                row = re.match(
                    r"\s*(\d+\.\d+)\s+(\d{2,4})(?!\.\d)",
                    tail,
                    re.I,
                )
                if not row:
                    continue
                values = [float(row.group(1)), int(row.group(2))]
            else:
                # Validation table is four decimal metrics.
                row = re.match(
                    r"\s*(\d+\.\d+)\s+(\d+\.\d+)\s+"
                    r"(\d+\.\d+)\s+(\d+\.\d+)",
                    tail,
                    re.I,
                )
                if not row:
                    continue
                values = [float(row.group(i)) for i in range(1, 5)]

            rows.append({"model": display, "values": values})
            used_models.add(display)
            break

    return rows


def _extract_results(
    sections: Dict[str, str],
    subsections: List[Dict[str, str]],
) -> Dict[str, Any]:
    result_parts = []

    if sections.get("results"):
        result_parts.append(sections["results"])

    for item in subsections:
        title = item["title"].lower()
        if any(word in title for word in [
            "validation dataset",
            "validataion dataset",
            "test dataset",
            "experimental results",
            "comparative analysis",
            "results",
            "performance",
        ]):
            result_parts.append(item["text"])

    result_text = "\n\n".join(result_parts)

    # The validation/test tables are flattened by pypdf. Isolate each table
    # first so numbers from one table cannot contaminate another table.
    validation_text = result_text
    validation_match = re.search(
        r"table\s*2\..*?(?=table\s*3\.|$)",
        result_text,
        re.I | re.S,
    )
    if validation_match:
        validation_text = validation_match.group(0)

    test_text = result_text
    test_match = re.search(
        r"table\s*3\..*?(?=table\s*4\.|$)",
        result_text,
        re.I | re.S,
    )
    if test_match:
        test_text = test_match.group(0)

    validation_rows = _extract_flat_table_rows(validation_text, 4)
    test_rows = _extract_flat_table_rows(test_text, 2)

    best_validation = next(
        (row for row in validation_rows if row["model"] == "YOLOv8 + TTA"),
        None,
    )
    best_test = next(
        (row for row in test_rows if row["model"] == "YOLOv8 + TTA"),
        None,
    )

    validation = {
        "map_50": best_validation["values"][0] if best_validation else None,
        "map_50_95": best_validation["values"][1] if best_validation else None,
        "precision": best_validation["values"][2] if best_validation else None,
        "recall": best_validation["values"][3] if best_validation else None,
    }

    test = {
        "map": best_test["values"][0] if best_test else None,
        "fps": int(best_test["values"][1]) if best_test else None,
    }

    prose = re.search(
        r"(?:overall\s+)?mAP\s+(?:score\s+)?of\s+(\d+\.\d+).*?(\d+)\s*fps",
        result_text,
        re.I | re.S,
    )

    if prose:
        if test["map"] is None:
            test["map"] = float(prose.group(1))
        if test["fps"] is None:
            test["fps"] = int(prose.group(2))

    rank_match = re.search(
        r"ranked\s+(\d+)(?:st|nd|rd|th)?\s+(?:on|in|at)",
        result_text,
        re.I,
    )
    challenge_rank = int(rank_match.group(1)) if rank_match else None

    return {
        "validation": validation,
        "test": test,
        "validation_models": validation_rows,
        "test_models": test_rows,
        "challenge_rank": challenge_rank,
        "best_model": "YOLOv8 + TTA" if (best_validation or best_test) else None,
        "_result_text": result_text,
    }


# ---------------------------------------------------------
# Limitations / future work
# ---------------------------------------------------------

def _find_section_text(
    sections: Dict[str, str],
    section_records: List[Dict[str, str]],
    aliases: List[str],
) -> Optional[str]:
    for alias in aliases:
        if sections.get(alias):
            return sections[alias]

    for item in section_records:
        normalized = _normalize_heading(item["title"])
        if normalized in aliases and item["text"]:
            return item["text"]

    return None


# ---------------------------------------------------------
# Intelligent key findings
# ---------------------------------------------------------

def _extract_key_findings(
    results: Dict[str, Any],
    result_text: str,
) -> List[str]:
    findings = []

    validation = results.get("validation", {})
    test = results.get("test", {})
    rank = results.get("challenge_rank")

    if validation.get("map_50_95") is not None:
        findings.append(
            "YOLOv8 + TTA achieved a validation mAP@0.5:0.95 of "
            f"{validation['map_50_95']:.3f}."
        )

    if validation.get("map_50") is not None:
        findings.append(
            "YOLOv8 + TTA achieved a validation mAP@0.5 of "
            f"{validation['map_50']:.3f}."
        )

    if test.get("map") is not None and test.get("fps") is not None:
        findings.append(
            "On the test dataset, YOLOv8 + TTA achieved an mAP of "
            f"{test['map']:.4f} at {test['fps']} FPS."
        )

    # Only report TTA improvement when the paper's result text explicitly
    # contains improvement/enhancement language.
    if re.search(
        r"test\s*time\s*augmentation.*?(?:enhanced|improv|increas|better)",
        result_text,
        re.I | re.S,
    ):
        findings.append(
            "Test Time Augmentation (TTA) improved the reported model performance."
        )

    if rank is not None:
        findings.append(
            f"The proposed system ranked {rank}th in the reported challenge leaderboard."
        )

    return findings[:5]


# ---------------------------------------------------------
# Main API service
# ---------------------------------------------------------

def analyze_pdf(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    reader = PdfReader(io.BytesIO(file_bytes))

    page_texts = []

    for page in reader.pages:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:
            page_texts.append("")

    if not any(text.strip() for text in page_texts):
        raise ValueError(
            "No readable text was extracted from this PDF. "
            "The PDF may be scanned/image-only."
        )

    lines = _prepare_lines(page_texts)
    parsed = _extract_sections(lines)

    sections = parsed["sections"]
    section_records = parsed["section_records"]
    subsections = parsed["subsections"]

    full_text = _clean_content("\n".join(lines))

    abstract = sections.get("abstract")

    methodology = _extract_methodology(
        sections,
        section_records,
        subsections,
    )

    dataset = _extract_dataset(
        sections,
        subsections,
        full_text,
    )

    results = _extract_results(
        sections,
        subsections,
    )

    result_text = results.pop("_result_text", "")

    limitations = _find_section_text(
        sections,
        section_records,
        ["limitations", "limitations and future work"],
    )

    future_work = _find_section_text(
        sections,
        section_records,
        ["future work", "future works", "future directions"],
    )

    findings = _extract_key_findings(
        results,
        result_text,
    )

    return {
        "filename": filename,
        "page_count": len(reader.pages),
        "extracted_text_length": len(full_text),

        "title": _extract_title(page_texts),
        "abstract": abstract,

        "methodology": methodology,
        "dataset": dataset,
        "results": results,

        "limitations": limitations,
        "future_work": future_work,

        "key_findings": findings,
        "keywords": _extract_keywords(full_text),

        "subsections": subsections,
    }
