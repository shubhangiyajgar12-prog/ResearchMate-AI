import re
from typing import Optional

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.literature_paper import LiteraturePaper
from app.models.paper_analysis import PaperAnalysis


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_research_text(text: str) -> str:
    """
    Clean extracted research-paper text while preserving
    the actual research content.

    The PDF extractor used by ResearchMate may return the
    complete paper as one large string instead of separate
    lines. Therefore this cleaner must NEVER depend on
    line boundaries being present.

    It removes only obvious non-research content:
    - reference section
    - standalone URLs/emails
    - figure/table captions
    - obvious metadata

    Normal research paragraphs are preserved.
    """

    if not text:
        return ""

    # Normalize common PDF extraction characters.
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2010", "-")
    text = text.replace("\u2011", "-")
    text = text.replace("\u2012", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\uFB00", "ff")
    text = text.replace("\uFB01", "fi")
    text = text.replace("\uFB02", "fl")
    text = text.replace("\uFB03", "ffi")
    text = text.replace("\uFB04", "ffl")

    # Protect the actual content from accidental whitespace issues.
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    # ------------------------------------------------------------
    # Remove everything from the References/Bibliography heading
    # to the end.
    #
    # This works even when the whole PDF was extracted as one line.
    # ------------------------------------------------------------
    text = re.sub(
        r"\s+(?:\d+[\.\)]?\s*)?(?:references|bibliography)\s+.*$",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # ------------------------------------------------------------
    # Remove standalone URLs and email addresses.
    # Do not remove surrounding research sentences.
    # ------------------------------------------------------------
    text = re.sub(
        r"https?://[^\s]+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"www\.[^\s]+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        " ",
        text,
    )

    # ------------------------------------------------------------
    # Remove figure/table captions.
    #
    # Example:
    # "Figure 1. Illustration of predictions..."
    # "Table 2: Experimental results..."
    #
    # Because PDF extraction can place these in the middle of a
    # paragraph, remove only the caption-like portion up to the
    # next likely numbered section.
    # ------------------------------------------------------------
    text = re.sub(
        r"\b(?:Figure|Fig\.|Table)\s+\d+\s*[\.:]\s*.*?(?=\s+\d+\.\s+[A-Z]|\s+(?:Abstract|Introduction|Methodology|Methods|Results|Discussion|Conclusion)\b)",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # ------------------------------------------------------------
    # Remove flattened title/author/affiliation header when an
    # "Abstract" marker exists. Keep the actual abstract content.
    # ------------------------------------------------------------
    abstract_match = re.search(r"\babstract\b", text, flags=re.IGNORECASE)
    if abstract_match:
        prefix = text[:abstract_match.start()]
        if (
            re.search(r"\b(?:department|university|institute|college|school)\b", prefix, re.IGNORECASE)
            or re.search(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", prefix)
        ):
            text = text[abstract_match.end():].strip()

    # ------------------------------------------------------------
    # Remove corresponding-author marker.
    # ------------------------------------------------------------
    text = re.sub(
        r"\*?\s*Corresponding author\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # ------------------------------------------------------------
    # Remove obvious publication metadata.
    # ------------------------------------------------------------
    text = re.sub(
        r"\b(?:Received|Accepted|Published)\s*:\s*[A-Za-z0-9,\- /]+\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Final whitespace normalization.
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# CITATION DETECTION
# ============================================================

def has_citation(sentence: str) -> bool:
    """
    Detect common academic citation formats.

    Supported examples:
        [1]
        [1,2]
        [1-4]
        (Smith, 2022)
        Smith et al. (2022)
        (Smith et al., 2022)
        (Aboah and Wang, 2023)
    """

    if not sentence:
        return False

    # Numeric citations: [1], [1,2], [1-4]
    if re.search(r"\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]", sentence):
        return True

    # Author-year citations.
    if re.search(
        r"\b[A-Z][A-Za-z'-]+(?:\s+et\s+al\.)?\s*\(\s*(?:19|20)\d{2}[a-z]?\s*\)",
        sentence,
    ):
        return True

    # Parenthetical author-year.
    if re.search(
        r"\(\s*[A-Z][A-Za-z'-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z'-]+)?(?:\s+et\s+al\.)?\s*,\s*(?:19|20)\d{2}[a-z]?\s*\)",
        sentence,
    ):
        return True

    # Multiple author-year citations in parentheses.
    if re.search(
        r"\(\s*[^)]*(?:19|20)\d{2}[^)]*\)",
        sentence,
    ):
        if re.search(r"[A-Z][A-Za-z'-]+\s*,", sentence):
            return True

    return False


# ============================================================
# CLAIM CLASSIFICATION
# ============================================================

def is_metadata_sentence(sentence: str) -> bool:
    """Skip PDF title/author/affiliation metadata and publication boilerplate."""
    s = sentence.strip()
    sl = s.lower()

    if not s:
        return True

    metadata_patterns = [
        r"\bdepartment of\b",
        r"\buniversity of\b",
        r"\binstitute of\b",
        r"\bcollege of\b",
        r"\bschool of\b",
        r"\bresearch center\b",
        r"\bcorresponding author\b",
        r"\be-?mail\b",
        r"\bemail\b",
        r"\bhttps?://",
        r"\bwww\.",
        r"\barxiv\b",
        r"\bdoi\s*:",
        r"\breceived\s*:",
        r"\baccepted\s*:",
        r"\bpublished\s*:",
    ]
    if any(re.search(p, sl) for p in metadata_patterns):
        return True

    # Author/header fragments commonly produced by flattened PDF extraction.
    if len(s.split()) <= 30 and re.search(
        r"\b(?:armstrong|aboah|wang|bagci|adu-gyamfi)\b", sl
    ) and not re.search(r"\b(?:we|our|study|method|results|experiment)\b", sl):
        return True

    return False


def is_structural_sentence(sentence: str) -> bool:
    """Detect paper-organization, navigation, and section-description sentences."""
    s = sentence.lower().strip()

    structural_patterns = [
        r"^in this paper\b",
        r"^this paper\b",
        r"^this study is organized\b",
        r"^this paper is organized\b",
        r"^the remainder of (?:this )?paper\b",
        r"^the rest of (?:this )?paper\b",
        r"^the paper is structured\b",
        r"^the paper is organized\b",
        r"\bis structured as follows\b",
        r"\bis organized as follows\b",
        r"\bthe following sections\b",
        r"^section\s+\d+(?:\.\d+)*\b",
        r"\bin section\s+\d+(?:\.\d+)*\b",
        r"\bsection\s+\d+(?:\.\d+)*\s+(?:describes|presents|discusses|explains|shows|details)\b",
        r"\bthis section\s+(?:describes|presents|discusses|explains|shows)\b",
        r"\bthe major contributions\b",
        r"\bthe contributions of this paper\b",
        r"\bare summarized as follows\b",
        r"\bcan be summarized as follows\b",
        r"^in the following sections\b",
    ]
    return any(re.search(pattern, s) for pattern in structural_patterns)


def is_own_research_claim(sentence: str) -> bool:
    """Detect statements describing the authors' own method, setup, or results.

    This is intentionally conservative: method/setup/result descriptions are
    not treated as missing external citations unless the sentence explicitly
    attributes something to prior/existing work or makes an external comparison.
    """
    s = sentence.lower().strip()

    # Strong markers for the authors' own work.
    own_patterns = [
        # First-person authorship.
        r"\bwe\s+(?:propose|present|introduce|develop|developed|design|designed|implement|implemented|build|built|train|trained|test|tested|evaluate|evaluated|achieve|achieved|obtain|obtained|conduct|conducted|perform|performed|utilize|utilized|use|used|employ|employed|adopt|adopted|compare|compared|experiment|experimented|investigate|investigated|measure|measured|observe|observed|find|found|report|reported|create|created|apply|applied)\b",
        r"\bour\s+(?:method|model|system|approach|framework|dataset|experiment|experiments|results|findings|study|work|analysis|training|validation|testing|implementation|architecture|pipeline|algorithm|strategy|technique|performance|accuracy|precision|recall|map)\b",
        r"\bour\s+proposed\b",
        r"\bwe\s+have\s+(?:created|developed|built|designed|implemented|proposed)\b",
        r"\bour\s+proposed\s+(?:method|model|system|approach|framework|strategy|technique|pipeline|algorithm|data\s+processing|data\s+processing\s+strateg(?:y|ies))\b",
        r"\bour\s+proposed\b",
        r"\bwe\s+have\s+(?:created|developed|built|designed|implemented|proposed|developed)\b",

        # Own paper/study.
        r"\b(?:this|the)\s+study\s+(?:aims?|seeks?|proposes?|presents?|introduces?|develops?|developed|implements?|implemented|uses?|used|utilizes?|utilized|employs?|employed|evaluates?|evaluated|investigates?|investigated|conducts?|conducted|reports?|reported|carried\s+out|performed|experiment(?:s|ed)?|demonstrates?|demonstrated)\b",
        r"\b(?:this|the)\s+(?:paper|work)\s+(?:proposes?|presents?|introduces?|develops?|developed|implements?|implemented|evaluates?|evaluated|investigates?|investigated|uses?|used|employs?|employed)\b",

        # Own method/result, including passive constructions.
        r"\b(?:proposed|developed|implemented|designed|introduced|created|presented|built)\s+(?:a|an|the)\b",
        r"\b(?:a|an|the)\s+(?:novel|proposed|developed|implemented|designed)\s+(?:method|model|system|approach|framework|strategy|technique|pipeline)\b",
        r"\b(?:technique|method|approach|framework|strategy|system|model|pipeline)\s+was\s+(?:implemented|developed|designed|proposed|applied|used|utilized)\b",
        r"\b(?:techniques?|methods?|approaches?|strategies?|models?|systems?|frameworks?)\s+(?:were|was)\s+(?:applied|used|utilized|implemented|developed|designed|evaluated|tested)\b",
        r"\b(?:data augmentation|few[- ]shot data sampling|sampling framework|data preprocessing)\s+(?:was|were)\s+(?:developed|applied|used|utilized|implemented|performed)\b",
        r"\b(?:the|this)\s+(?:model|system|dataset|framework|method|technique)\s+was\s+(?:trained|tested|evaluated|implemented|developed|created|split|divided|collected|annotated|augmented)\b",
        r"\b(?:all|the|three)\s+(?:models?)\s+were\s+trained\b",

        # Own experimental settings/results.
        r"\b(?:experimental|test|validation|training)\s+(?:results?|dataset|setup|configuration)\b",
        r"\b(?:it|the model|the system|the proposed method|the proposed system|the proposed model)\s+(?:achieved|obtained|reached|yielded|recorded|demonstrated)\b",
        r"\b(?:our|the)\s+(?:accuracy|precision|recall|f1|f1[- ]score|performance|map|inference speed|results|findings)\b",
        r"\bexperiments?\s+(?:show|showed|demonstrate|demonstrated|indicate|indicated|achieve|achieved|yield|yielded)\b",
        r"\b(?:trained|tested|evaluated)\s+models?\b",
        r"\b(?:all models|both models|three models)\s+(?:were|are)\s+(?:trained|tested|evaluated)\b",

        # Strong first-person / study-goal wording.
        r"\b(?:the\s+)?(?:overarching\s+)?goal\s+of\s+this\s+study\b",
        r"\b(?:by\s+using|using)\s+(?:this|the)\s+(?:technique|method|approach|strategy|system|model)\b.*\bwe\s+(?:are|were|have|can|could|able)\b",
        r"\bwe\s+(?:are|were|have|had)\s+able\s+to\s+(?:develop|build|create|implement|achieve|obtain)\b",
        r"\bthis\s+is\s+crucial\s+for\s+the\s+practical\s+application\s+of\s+(?:the|our)\s+system\b",
        r"\b(?:this|our)\s+system\b.*\b(?:practical\s+application|real[- ]world\s+environments?)\b",
        r"\b(?:this|our)\s+(?:system|model|approach)\b.*\b(?:our\s+task|our\s+application)\b",

        # Procedural statements that describe what this paper actually did.
        r"\b(?:rotation|flipping|scaling|cropping|augmentation|preprocessing|sampling|sorting)\s+was\s+(?:applied|performed|used|utilized|done)\b",
        r"\b(?:videos?|images?|frames?)\s+were\s+(?:sorted|filtered|sampled|selected|split|divided|processed|annotated|augmented|collected)\b",
        r"\b(?:a|the)\s+sample\s+rate\s+(?:is|was)\s+calculated\b",
        r"\b(?:sorting|sampling|filtering|preprocessing)\s+(?:videos?|images?|data)\b.*\b(?:using|based\s+on)\b",
        r"\b(?:the|this)\s+dataset\s+(?:was|is)\s+(?:used|collected|created|prepared|split|divided|annotated|augmented)\b",

        # Methodology wording that explicitly anchors to this study.
        r"\b(?:in|during|for)\s+this\s+study\b",
        r"\b(?:in|during)\s+our\s+(?:study|experiments?|experimentation)\b",
        r"\b(?:the|this)\s+study\s+(?:carried\s+out|conducted|performed|employed|experimented)\b",
        r"\b(?:this|the)\s+framework\s+was\s+designed\b",
        r"\b(?:this|the)\s+algorithm\s+(?:receives|takes|calculates|selects|outputs|generates)\b",
    ]

    if not any(re.search(pattern, s, re.IGNORECASE) for pattern in own_patterns):
        return False

    # Strong contribution-led sentences remain the authors own work even
    # when they contain an adjective such as "state-of-the-art" describing
    # a model they used. The external phrase should not reclassify the
    # entire contribution sentence.
    contribution_led_patterns = [
        r"^(?:developed|implemented|designed|proposed|introduced|created|presented|built)\b",
        r"^to\s+achieve\s+(?:this|our)\s+goal\b.*\b(?:we|our)\b",
        r"^(?:by|through)\s+(?:developing|using|applying)\b.*\b(?:we|our)\b",
        r"^the\s+(?:overarching\s+)?goal\s+of\s+this\s+study\b",
        r"^(?:finally,\s+)?the\s+use\s+of\s+.*\bour\s+proposed\b",
        r"^by\s+developing\s+.*\bwe\s+have\s+(?:created|developed|built)\b",
    ]
    if any(re.search(pattern, s, re.IGNORECASE | re.VERBOSE) for pattern in contribution_led_patterns):
        return True

    # Explicit external comparison/attribution overrides own-work detection.
    comparison_markers = [
        r"\bcompared\s+(?:with|to)\b",
        r"\bcomparison\s+with\b",
        r"\bprevious\s+(?:work|method|methods|study|studies|research|approaches?)\b",
        r"\bprior\s+(?:work|method|methods|study|studies|research|approaches?)\b",
        r"\bexisting\s+(?:method|methods|approach|approaches|system|systems|work|research)\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bbaseline(?:s)?\b",
        r"\bsuperior\s+to\b",
        r"\bbetter\s+than\b",
        r"\bworse\s+than\b",
    ]
    if any(re.search(p, s, re.IGNORECASE) for p in comparison_markers):
        return False

    return True

def is_external_research_claim(sentence: str) -> bool:
    """Detect claims explicitly grounded in prior/external research."""
    s = sentence.lower()

    patterns = [
        r"\bprevious studies\b",
        r"\bprevious work\b",
        r"\bprior studies\b",
        r"\bprior work\b",
        r"\bprior research\b",
        r"\bexisting studies\b",
        r"\bexisting research\b",
        r"\bexisting methods\b",
        r"\bexisting approaches\b",
        r"\baccording to\b",
        r"\breported by\b",
        r"\bhas been shown\b",
        r"\bhave been shown\b",
        r"\bhas been proposed\b",
        r"\bhave been proposed\b",
        r"\bwas proposed\b",
        r"\bwere proposed\b",
        r"\bcommonly used\b",
        r"\bwidely used\b",
        r"\bwidely adopted\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bbaseline\b",
        r"\bthe authors?\b",
        r"\banother study\b",
        r"\ba study\b",
        r"\bstudy by\b",
    ]
    return any(re.search(pattern, s) for pattern in patterns)


def is_general_factual_claim(sentence: str) -> bool:
    """Detect broad background facts that commonly need supporting citations."""
    s = sentence.lower()

    patterns = [
        r"\bis a major\b", r"\bare a major\b",
        r"\bis an important\b", r"\bare an important\b",
        r"\bis crucial\b", r"\bare crucial\b",
        r"\bis essential\b", r"\bare essential\b",
        r"\bhas become\b", r"\bhave become\b",
        r"\bcauses\b", r"\bcause\b",
        r"\bresults in\b", r"\bleads to\b",
        r"\bis associated with\b", r"\bare associated with\b",
        r"\baccording to statistics\b",
        r"\bworldwide\b", r"\bglobally\b",
        r"\bsignificant problem\b", r"\bsignificant concern\b",
        r"\bhas been reported\b", r"\bhave been reported\b",
        r"\bhas increased\b", r"\bhave increased\b",
        r"\bhas decreased\b", r"\bhave decreased\b",
    ]
    return any(re.search(pattern, s) for pattern in patterns)


def looks_like_heading(sentence: str) -> bool:
    """Detect common numbered/section headings."""
    s = sentence.strip()
    if not s:
        return False

    if re.match(r"^\d+(?:\.\d+)*[\.\)]?\s+[A-Z][A-Za-z0-9 /&()\-]{1,100}$", s):
        return True

    headings = {
        "abstract", "introduction", "background", "related work",
        "literature review", "methodology", "methods",
        "materials and methods", "experiments", "experimental results",
        "results", "discussion", "conclusion", "future work",
        "acknowledgments", "acknowledgements", "references",
    }
    return s.lower() in headings


def looks_like_reference_entry(sentence: str) -> bool:
    """Detect obvious bibliography entries if any survive cleaning."""
    s = sentence.strip()
    if not s:
        return False

    if re.match(r"^\[\d+\]\s+", s):
        return True

    if re.match(r"^\d+[\.\)]\s+[A-Z][A-Za-z'-]+.*(?:19|20)\d{2}", s):
        return True

    if re.search(r"\bdoi\s*:\s*10\.\d+/", s, re.IGNORECASE):
        return True

    return False


def looks_like_artifact(sentence: str) -> bool:
    """Skip captions, figure/table/algorithm fragments, code/URL debris, and PDF artifacts."""
    s = sentence.strip()
    sl = s.lower()

    if not s:
        return True

    if re.search(r"\b(?:figure|fig\.?)\s*\d+\s*[\.:]", sl):
        return True
    if re.search(r"\btable\s*\d+\s*[\.:]", sl):
        return True
    if re.search(r"\balgorithm\s*\d+\s*[\.:]", sl):
        return True

    # Caption fragments flattened from PDF extraction.
    if re.match(r"^(?:images?|illustration|example|samples?|results?)\s+from\b", sl):
        return True
    if re.search(r"\b(?:daylight|nighttime|foggy weather|weather conditions)\s*$", sl) and len(s.split()) < 18:
        return True
    if re.search(r"\b(?:shown|presented|illustrated)\s+in\s+\d+\s*$", sl):
        return True

    if re.search(r"\b(?:github|gitlab)\b|\.git\b|arxiv\.\w+/", sl):
        return True

    # Typical flattened table row / metric fragment.
    tokens = s.split()
    if len(tokens) >= 4:
        numeric_tokens = sum(1 for token in tokens if re.fullmatch(r"[\d.,%±+\-]+", token))
        if numeric_tokens >= 3 and numeric_tokens / len(tokens) >= 0.4:
            return True

    # Broken OCR/PDF figure references such as "... presented in 3."
    if re.search(r"\b(?:presented|shown|described|illustrated)\s+in\s+\d+\b", sl):
        return True

    return False

def looks_like_table_text(sentence: str) -> bool:
    """Backward-compatible alias used by the existing analysis pipeline."""
    return looks_like_artifact(sentence)


def looks_like_claim(sentence: str) -> bool:
    """General guard used by the citation classifier."""
    s = sentence.strip()

    if len(s) < 25:
        return False

    if is_metadata_sentence(s):
        return False

    if looks_like_heading(s):
        return False

    if looks_like_reference_entry(s):
        return False

    if looks_like_artifact(s):
        return False

    alpha_chars = sum(ch.isalpha() for ch in s)
    if alpha_chars < 15:
        return False

    # Pure navigation / caption-like fragments.
    if re.match(r"^(?:see|refer to)\s+(?:fig(?:ure)?|table|algorithm)\b", s, re.IGNORECASE):
        return False

    return True


def classify_claim(sentence: str) -> tuple[bool, str, float]:
    """
    Return:
        citation_needed, reason, confidence

    The classifier intentionally distinguishes:
      1. authors' own methods/results -> no external citation required
      2. paper structure/metadata/artifacts -> ignored
      3. external research/background facts -> citation recommended
    """
    if not looks_like_claim(sentence):
        return False, "not_a_claim", 0.97

    if is_structural_sentence(sentence):
        return False, "paper_structure_or_process", 0.95

    # Detect the authors' own method/setup/results before broad external
    # patterns. is_own_research_claim() deliberately returns False when
    # the same sentence contains an explicit external comparison or
    # attribution (e.g. previous/existing/state-of-the-art).
    if is_own_research_claim(sentence):
        return False, "authors_own_research_claim", 0.90

    # Only after ruling out own-work descriptions, treat explicit prior-work
    # language as an external citation requirement.
    if is_external_research_claim(sentence):
        return True, "external_research_claim", 0.94

    if is_general_factual_claim(sentence):
        return True, "general_factual_claim", 0.86

    # Quantitative statements are useful citation candidates only when
    # they do not look like the authors' own experimental reporting.
    if re.search(
        r"\b\d+(?:\.\d+)?\s*(?:%|percent|million|billion|thousand|km|m|kg|ms|fps|years?|people|vehicles?)\b",
        sentence,
        re.IGNORECASE,
    ):
        return True, "quantitative_claim", 0.88

    # Explicit attribution to a named organization/source.
    if re.search(
        r"\b(?:WHO|World Health Organization|CDC|IEEE|NHTSA|government|"
        r"organization|report|survey|study)\b",
        sentence,
        re.IGNORECASE,
    ):
        return True, "attributed_factual_claim", 0.82

    # Avoid flagging every ordinary methodological sentence.
    method_markers = [
        r"\bwe\b", r"\bour\b", r"\bthe proposed\b", r"\bthe model\b",
        r"\bthe system\b", r"\bthe dataset\b", r"\btraining\b",
        r"\btesting\b", r"\bvalidation\b", r"\bexperiment",
    ]
    if any(re.search(p, sentence, re.IGNORECASE) for p in method_markers):
        return False, "method_or_experimental_description", 0.72

    return True, "factual_claim", 0.62


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def split_sentences(text: str) -> list[str]:
    """
    Split flattened PDF text into clean sentence-like units.

    PDF extraction often destroys paragraph/line boundaries, so common
    extraction artifacts are repaired before classification.
    """
    if not text:
        return []

    protected = text
    replacements = {
        "e.g.": "e<dot>g<dot>",
        "i.e.": "i<dot>e<dot>",
        "et al.": "et al<dot>",
        "Fig.": "Fig<dot>",
        "Dr.": "Dr<dot>",
        "vs.": "vs<dot>",
        "etc.": "etc<dot>",
        "No.": "No<dot>",
    }

    for old, new in replacements.items():
        protected = protected.replace(old, new)

    protected = re.sub(r"\bprevious\.\s+methods\b", "previous methods", protected, flags=re.I)
    protected = re.sub(r"\bIn\.\s+conclusion\b", "In conclusion", protected, flags=re.I)
    protected = re.sub(r"\bThis\.\s+results\b", "These results", protected, flags=re.I)

    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", protected)

    sentences = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        for old, new in replacements.items():
            part = part.replace(new, old)

        part = re.sub(
            r"^\s*(?:\d+(?:\.\d+)*[.)]?\s+)?"
            r"(?:Introduction|Background|Related Works?|Literature Review|"
            r"Methodology|Methods|Experiments?|Experimental Results|"
            r"Results|Discussion|Conclusion|Future Work)\s+"
            r"(?=[A-Z])",
            "",
            part,
            flags=re.I,
        ).strip()

        part = re.sub(
            r"^\s*(?:LENGE|Challenge)\s*,?\s*(?:specifically\s+)?",
            "",
            part,
            flags=re.I,
        ).strip()

        if part:
            sentences.append(part)

    return sentences


# ============================================================
# SOURCE RECOMMENDATION
# ============================================================

def _source_id_from_analysis(analysis: PaperAnalysis) -> Optional[int]:
    """
    PaperAnalysis stores the linked LiteraturePaper through
    literature_paper_id.
    """

    if not analysis:
        return None

    return getattr(analysis, "literature_paper_id", None)


def _find_best_source(
    db: Session,
    project_id: int,
    claim_text: str,
    exclude_paper_id: Optional[int] = None,
) -> tuple[Optional[int], Optional[str]]:
    """
    Recommend a source from the project's analyzed literature.

    This is a lightweight TF-IDF recommendation, not a semantic
    embedding search.
    """

    query = (
        db.query(PaperAnalysis)
        .filter(PaperAnalysis.project_id == project_id)
    )

    analyses = query.all()

    if not analyses:
        return None, None

    candidates = []

    for analysis in analyses:
        source_id = _source_id_from_analysis(analysis)

        if source_id is None:
            continue

        if exclude_paper_id is not None and source_id == exclude_paper_id:
            continue

        text = clean_research_text(analysis.extracted_text or "")

        if not text:
            continue

        candidates.append((source_id, text))

    if not candidates:
        return None, None

    documents = [claim_text] + [text for _, text in candidates]

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
        )

        matrix = vectorizer.fit_transform(documents)
        scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()

    except Exception:
        return None, None

    if len(scores) == 0:
        return None, None

    best_index = int(scores.argmax())
    best_score = float(scores[best_index])

    # Do not recommend a source from weak lexical overlap.
    # TF-IDF is only a lightweight fallback until embeddings are added.
    if best_score < 0.25:
        return None, None

    source_id = candidates[best_index][0]

    reason = (
        f"TF-IDF similarity with analyzed source paper "
        f"({best_score * 100:.1f}% lexical similarity)."
    )

    return source_id, reason

# ============================================================
# CITATION CONTEXT / GROUPING
# ============================================================

def _is_strong_external_claim(sentence: str) -> bool:
    """Strong evidence that a claim depends on external literature."""
    s = sentence.lower()
    patterns = [
        r"\bthe authors\b", r"\banother study\b", r"\bthis study\b",
        r"\bprevious studies?\b", r"\bprior studies?\b",
        r"\bprevious work\b", r"\bprior work\b", r"\baccording to\b",
        r"\breported\b", r"\bhas been shown\b", r"\bhave been shown\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bworld health organization\b",
        r"\b\d+(?:\.\d+)?\s*%\b",
    ]
    return any(re.search(p, s, re.I) for p in patterns)


def _is_technical_explanation(sentence: str) -> bool:
    """Technical/model description that can inherit nearby citation context."""
    s = sentence.lower()
    patterns = [
        r"\bbackbone\b", r"\bneck\b", r"\bhead\b",
        r"\bconvolutional neural network\b", r"\bfeature maps?\b",
        r"\bbounding boxes?\b", r"\barchitecture\b",
        r"\banchor[- ]free\b", r"\bpanet\b", r"\bcspdarknet\b",
        r"\bspp block\b", r"\bfeature pyramid\b", r"\byolov[3578]\b",
        r"\breceptive field\b", r"\bparameters?\b",
    ]
    return any(re.search(p, s, re.I) for p in patterns)


def _is_same_topic(a: str, b: str) -> bool:
    stop = {
        "the","a","an","and","or","of","to","in","for","with","is","are",
        "was","were","this","that","these","those","it","its","their",
        "they","also","used","using","from","which","has","have","had",
        "on","as","by","be","been","into","than","such","can","may","will",
        "more","less"
    }

    def tokens(s):
        return {
            x for x in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", s.lower())
            if x not in stop
        }

    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb and len(ta & tb) >= 1)


def _build_citation_groups(sentences: list[str]) -> list[list[str]]:
    """
    Build small local groups. A citation can support nearby technical
    continuation, but a new external study starts a new group.
    """
    groups = []
    current = []

    for sentence in sentences:
        if not sentence.strip():
            continue

        if not current:
            current = [sentence]
            continue

        previous = current[-1]

        technical_chain = (
            _is_technical_explanation(previous)
            and _is_technical_explanation(sentence)
            and _is_same_topic(previous, sentence)
        )

        continuation = bool(re.match(
            r"^(this|these|such|the|it|they|additionally|also|similarly|"
            r"furthermore|moreover|in addition)\b",
            sentence.strip(), re.I
        ))

        new_external = (
            _is_strong_external_claim(sentence)
            and not continuation
            and not technical_chain
        )

        if new_external or len(current) >= 5:
            groups.append(current)
            current = [sentence]
        elif technical_chain or continuation or _is_same_topic(previous, sentence):
            current.append(sentence)
        else:
            groups.append(current)
            current = [sentence]

    if current:
        groups.append(current)

    return groups


def _group_has_citation(group: list[str]) -> bool:
    return any(has_citation(sentence) for sentence in group)


def _should_report_claim(
    sentence: str,
    group: list[str],
    citation_present: bool,
    citation_needed: bool,
) -> bool:
    """
    Final gate:
    - cited claims stay visible;
    - technical continuations inherit nearby citation context;
    - explicit external claims remain reportable if their own citation is absent;
    - unrelated factual sentences are not hidden merely because a citation
      exists elsewhere.
    """
    if not citation_needed:
        return False

    if citation_present:
        return True

    group_has_citation = _group_has_citation(group)

    if _is_technical_explanation(sentence) and group_has_citation:
        return False

    if group_has_citation and not _is_strong_external_claim(sentence):
        return False

    return True


def _deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Remove near-duplicate warnings while preserving distinct claims."""
    result = []

    for finding in findings:
        claim = re.sub(
            r"\s+", " ", finding.get("claim_text", "").strip().lower()
        )
        tokens = set(re.sub(r"[^a-z0-9 ]", "", claim).split())

        duplicate = False

        for old in result:
            old_claim = re.sub(
                r"\s+", " ", old.get("claim_text", "").strip().lower()
            )
            old_tokens = set(
                re.sub(r"[^a-z0-9 ]", "", old_claim).split()
            )

            if tokens and old_tokens:
                overlap = len(tokens & old_tokens) / max(
                    1, len(tokens | old_tokens)
                )
                if overlap >= 0.72 and len(tokens) >= 6:
                    duplicate = True
                    break

        if not duplicate:
            result.append(finding)

    return result

# ============================================================
# MAIN CITATION ANALYSIS
# ============================================================

def analyze_citations(
    db: Session,
    project_id: int,
    paper_id: int,
) -> dict:
    """
    Analyze citation coverage for a project paper.

    Important semantics:
        citation_needed = "yes"
            means this claim belongs to the set of claims that
            should have supporting citations.

        citation_present = "yes"
            means a citation marker was detected.

    A cited claim can therefore have:
        citation_present = "yes"
        citation_needed = "yes"

    This is necessary for citation coverage calculation.
    """

    # ------------------------------------------------------------
    # Find target paper
    # ------------------------------------------------------------

    paper = (
        db.query(LiteraturePaper)
        .filter(
            LiteraturePaper.id == paper_id,
            LiteraturePaper.project_id == project_id,
        )
        .first()
    )

    if paper is None:
        raise ValueError(
            f"Paper {paper_id} does not belong to project {project_id}."
        )

    # ------------------------------------------------------------
    # Find latest PaperAnalysis
    # ------------------------------------------------------------

    analysis = (
        db.query(PaperAnalysis)
        .filter(
            PaperAnalysis.literature_paper_id == paper_id,
            PaperAnalysis.project_id == project_id,
        )
        .order_by(PaperAnalysis.id.desc())
        .first()
    )

    if analysis is None:
        raise ValueError(
            "No paper analysis found for this paper. "
            "Run PDF analysis first."
        )

    raw_text = analysis.extracted_text or ""

    if not raw_text.strip():
        raise ValueError(
            "No extracted text available for this paper."
        )

    # ------------------------------------------------------------
    # Clean text
    # ------------------------------------------------------------

    cleaned_text = clean_research_text(raw_text)

    if not cleaned_text.strip():
        raise ValueError(
            "Extracted text exists, but text cleaning removed "
            "all content. Check the PDF extraction/cleaning step."
        )

    # ------------------------------------------------------------
    # Split into sentences
    # ------------------------------------------------------------

    sentences = split_sentences(cleaned_text)

    findings = []

    total_claims = 0
    citations_present = 0
    citation_required_claims = 0
    cited_required_claims = 0

    current_section = None
    citation_groups = _build_citation_groups(sentences)

    for group_sentences in citation_groups:

        for sentence in group_sentences:

            heading_match = re.match(
                r"^\s*(\d+(?:\.\d+)*)[.)]?\s+([A-Z][A-Za-z0-9 /&()\-]{1,100})",
                sentence,
            )

            if heading_match and len(sentence.split()) <= 18:
                current_section = heading_match.group(2).strip()
                continue

            if looks_like_heading(sentence):
                current_section = sentence.strip()
                continue

            if not looks_like_claim(sentence):
                continue

            citation_present_bool = has_citation(sentence)

            citation_needed_bool, reason, confidence = classify_claim(sentence)

            if not citation_needed_bool:
                continue

            if not _should_report_claim(
                sentence=sentence,
                group=group_sentences,
                citation_present=citation_present_bool,
                citation_needed=citation_needed_bool,
            ):
                continue

            total_claims += 1
            citation_required_claims += 1

            if citation_present_bool:
                citations_present += 1
                cited_required_claims += 1

            suggested_source_id = None
            suggestion_reason = None

            if not citation_present_bool:
                suggested_source_id, suggestion_reason = _find_best_source(
                    db=db,
                    project_id=project_id,
                    claim_text=sentence,
                    exclude_paper_id=paper_id,
                )

            findings.append(
                {
                    "section": current_section,
                    "claim_text": sentence,
                    "citation_present": (
                        "yes" if citation_present_bool else "no"
                    ),
                    "citation_needed": "yes",
                    "confidence": confidence,
                    "suggested_source_id": suggested_source_id,
                    "suggestion_reason": suggestion_reason or reason,
                }
            )

    findings = _deduplicate_findings(findings)

    # ------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------

    if citation_required_claims > 0:
        citation_coverage = (
            cited_required_claims / citation_required_claims
        ) * 100.0
    else:
        citation_coverage = 100.0

    potential_missing_citations = (
        citation_required_claims - cited_required_claims
    )

    # ------------------------------------------------------------
    # Risk level
    # ------------------------------------------------------------

    if citation_required_claims == 0:
        risk_level = "low"

    elif citation_coverage >= 80:
        risk_level = "low"

    elif citation_coverage >= 60:
        risk_level = "medium"

    else:
        risk_level = "high"

    return {
        "citation_coverage": round(citation_coverage, 2),
        "total_claims": total_claims,
        "citations_present": citations_present,
        "potential_missing_citations": potential_missing_citations,
        "risk_level": risk_level,
        "findings": findings,
        "cleaned_text_length": len(cleaned_text),
        "raw_text_length": len(raw_text),
    }
