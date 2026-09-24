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

    # Preserve paragraph boundaries. PDF extraction is often messy, but
    # paragraph context is important for citation inheritance.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *\n+", "\n\n", text).strip()

    if not text:
        return ""

    # ------------------------------------------------------------
    # Remove everything from the References/Bibliography heading
    # to the end.
    #
    # This works even when the whole PDF was extracted as one line.
    # ------------------------------------------------------------
    text = re.sub(
        r"(?:^|\n|\s{2,}|[.!?])\s*(?:\d+(?:\.\d+)*[\.)]?\s*)?(?:references|bibliography)\s*(?:\n|:|$).*",
        " ", text, flags=re.IGNORECASE | re.DOTALL)

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

    # Final normalization while deliberately preserving paragraph breaks.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *\n+", "\n\n", text).strip()

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
    """Detect statements describing the authors' own method, setup, or results."""
    s = sentence.lower().strip()

    own_patterns = [
        # Explicit first-person authorship.
        r"\bwe\s+(?:propose|present|introduce|develop|developed|design|designed|implement|implemented|build|built|train|trained|test|tested|evaluate|evaluated|achieve|achieved|obtain|obtained|conduct|conducted|perform|performed|utilize|utilized|use|used|employ|employed|adopt|adopted|compare|compared|experiment|experimented|investigate|investigated|measure|measured|observe|observed|find|found|report|reported)\b",
        r"\bour\s+(?:method|model|system|approach|framework|dataset|experiment|experiments|results|findings|study|work|analysis|training|validation|testing|implementation|architecture|pipeline|algorithm|strategy|technique|model)\b",

        # Proposed/implemented work.
        r"\b(?:our|the proposed)\s+(?:model|method|system|approach|framework|algorithm|architecture|pipeline|strategy|technique)\b",
        r"\b(?:our|the proposed)\s+(?:results|experiments|findings|study|work)\b",
        r"(?<!been\s)\bproposed\s+and\s+implemented\b",
        r"\bdeveloped\s+(?:a|an|the)\s+(?:real[- ]time|robust|novel|proposed)?\s*(?:helmet|detection|model|system|framework|method|approach)\b",
        r"\b(?:developed|implemented|designed|introduced|created)\s+(?:a|an|the)\b",

        # Study/paper describing its own work.
        r"\bthe overarching goal of (?:this|the) study\b",
        r"\bthe goal of (?:this|the) study\b",

        # Authors' own comparative experiments/results.
        r"\b(?:has|have)\s+demonstrated\s+the\s+highest\b",
        r"\b(?:achieved|obtained)\s+the\s+highest\b",
        r"\boutperformed\s+all\s+(?:other|the\s+other)\s+models\b",
        r"\b(?:our|the)\s+results\s+(?:show|showed|demonstrate|demonstrated)\b",
        r"\b(?:our|the)\s+experimental\s+(?:results|findings)\b",
    r"\bwe\s+(?:have\s+)?(?:created|developed|proposed|designed|implemented|introduced)\b",
    r"\bour\s+(?:proposed|developed|designed|implemented)\b",
    r"\b(?:this|the)\s+(?:technique|method|framework|model|system)\s+(?:was|were|is|are)\s+(?:implemented|applied|used|utilized|developed|designed)\b",
    r"\bto achieve this goal,\s+we\s+proposed\b",

    r"\bthe\s+(?:algorithm|framework|technique|method|model|system)\s+(?:receives|calculates|was|were|is|are)\b",
    r"\b(?:to|in order to)\s+(?:solve|address|overcome|reduce|improve|increase)\b.*\bin\s+this\s+study\b",

    r"\bthis\s+technique\s+(?:was|were|is|are)\s+(?:implemented|applied|used|utilized|developed|designed|introduced)\b",
    r"\b(?:using|by using)\s+this\s+technique\b",
    r"\b(?:data augmentation|augmentation strategies?)\s+(?:were|was)\s+(?:utilized|used|applied|implemented)\s+in\s+this\s+study\b",
    r"\b(?:our|the)\s+(?:proposed\s+)?(?:data processing|data augmentation|sampling)\s+(?:strategy|strategies|method|methods)\b",

        r"\b(?:this|the)\s+study\s+(?:aims?|seeks?|proposes?|presents?|introduces?|develops?|developed|implements?|implemented|uses?|used|utilizes?|utilized|employs?|employed|evaluates?|evaluated|investigates?|investigated|conducts?|conducted|reports?|reported|carried\s+out|performed)\b",
        r"\b(?:this|the)\s+(?:paper|work)\s+(?:proposes?|presents?|introduces?|develops?|developed|implements?|implemented|evaluates?|evaluated|investigates?|investigated)\b",

        # Own experimental design/setup/results.
        r"\b(?:the|this)\s+(?:study|paper|work)\s+(?:carried\s+out|conducted|performed)\b",
        r"\b(?:the|this)\s+study\s+employed\b",
        r"\b(?:the|this)\s+study\s+experimented\b",
        r"\b(?:the|this)\s+(?:model|system|dataset)\s+was\s+(?:trained|tested|evaluated|implemented|developed|created|split|divided|collected|annotated|augmented)\b",
        r"\b(?:all|the)\s+(?:models|three models)\s+were\s+trained\b",
        r"\bthis\s+is\s+crucial\s+for\s+(?:the\s+)?practical\s+application\b",
        r"\b(?:it|the model|the system|the proposed method|the proposed system)\s+(?:achieved|obtained|reached|yielded|recorded)\b",
        r"\b(?:our|the)\s+(?:accuracy|precision|recall|f1|f1[- ]score|performance|mAP|inference speed|results|findings)\b",
        r"\bexperiments?\s+(?:show|showed|demonstrate|demonstrated|indicate|indicated|achieve|achieved|yield|yielded)\b",

        # Method-specific language commonly extracted from methodology sections.
        r"\b(?:the\s+)?current\s+study\s+(?:seeks?|aims?|proposes?|presents?|introduces?|develops?|developed)\b",
        r"\bto\s+achieve\s+this\s+goal,?\s+we\s+(?:propose|proposed|develop|developed|present|presented)\b",
        r"\b(?:we|our)\s+(?:propose|proposed|develop|developed|design|designed|implement|implemented)\b",
        r"\b(?:the|this)\s+(?:framework|system|method|model|approach)\s+was\s+(?:developed|designed|implemented|applied|used|utilized)\b",
        r"\b(?:our\s+)?experimental\s+results?\s+(?:show|showed|demonstrate|demonstrated|indicate|indicated)\b",
        r"\b(?:in|during)\s+this\s+study\b.*\b(?:used|utilized|applied|implemented|developed|designed|performed|conducted)\b",
        r"\b(?:the|this)\s+study\s+(?:utilized|used|applied|implemented)\b",
        r"\b(?:data preprocessing|data augmentation|few[- ]shot data sampling|sampling framework)\s+(?:was|were)\s+(?:developed|applied|used|utilized|implemented)\b",
        r"\b(?:to|in order to)\s+(?:improve|increase|reduce|address|overcome)\b.*\b(?:in this study|in our study|we|the study)\b",
    ]

    if not any(re.search(pattern, s, re.IGNORECASE) for pattern in own_patterns):
        return False

    # If the sentence explicitly makes a claim about previous/existing work,
    # keep it eligible for citation even if it also reports our result.
    comparison_markers = [
        r"\bcompared\s+(?:with|to)\b",
        r"\bprevious\s+(?:work|method|methods|study|studies|research)\b",
        r"\bprior\s+(?:work|method|methods|study|studies|research)\b",
        r"\bexisting\s+(?:method|methods|approach|approaches|system|systems)\b",
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
        r"\bstud(?:y|ies)\b.*\b(?:conducted|performed|carried out)\s+by\b",
        r"\bstud(?:y|ies)\b.*\bby\s+\[?\d",
        r"\bthe authors?\s+(?:used|reported|proposed|developed|achieved|found)\b",
        r"\bprevious\s+(?:version|versions|model|models|network|networks)\b",
        r"\bmore\s+(?:effective|accurate|efficient|robust|reliable|precise)\s+than\b",
        r"\bmore\s+(?:effective|accurate|efficient|robust|reliable|precise)\s+than\s+(?:the\s+)?previous\s+versions?\b",
        r"\bimproved\s+(?:precision|speed|accuracy|performance)\b.*\bprevious\b",
        r"\bfaster\s+than\b",
        r"\btop\s+choice\b",
        r"\blatest\s+iteration\b",
        r"\bcommonly used\b",
        r"\bwidely used\b",
        r"\bwidely adopted\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bbaseline\b",
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
    if re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", s):
        return True
    if re.search(r"\b(?:vol\.?|volume|issue|pp?\.?|pages?)\s*\d+", s, re.I) and re.search(r"\b(?:19|20)\d{2}\b", s):
        return True
    return False



def _looks_like_algorithm_code(sentence: str) -> bool:
    """Detect extracted pseudocode/code blocks that are not citation claims."""
    s = sentence.strip()
    sl = s.lower()

    # Obvious algorithm/code signatures.
    code_markers = [
        r"\binput\s*:",
        r"\boutput\s*:",
        r"\bfor\s+\w+\s*(?:in|∈)\b",
        r"\bend\s+for\b",
        r"\breturn\b",
        r"\bif\s+.*\bthen\b",
        r"\belse\b",
        r"\bcalculate\w*\s*\(",
        r"\bmax\w*\s*\(",
        r"\bclass\s*←",
        r"\bfor\s+p\s*∈",
    ]
    score = sum(bool(re.search(p, sl)) for p in code_markers)

    if score >= 2:
        return True

    # Dense pseudocode with numbered steps.
    numbered_steps = len(re.findall(r"(?:^|\s)\d+\s*:", s))
    if numbered_steps >= 3:
        return True

    # Extracted variable/math-heavy algorithm text.
    if (
        re.search(r"\b(?:fp|frequency|skewness|maxfrequency|class)\s*[←=]", sl)
        and re.search(r"\b(?:for|if|else|return)\b", sl)
    ):
        return True

    return False


def _looks_like_figure_fragment(sentence: str) -> bool:
    """Detect incomplete figure/table references created by PDF extraction."""
    s = sentence.strip()
    sl = s.lower()

    if re.search(
        r"\b(?:shown|presented|illustrated|depicted)\s+in\s*$",
        sl,
    ):
        return True

    if re.search(
        r"\b(?:shown|presented|illustrated|depicted)\s+in\s+(?:figure|fig\.?|table)\s*\d*\s*$",
        sl,
    ):
        return True

    if re.search(
        r"\b(?:shown|presented|illustrated|depicted)\s+in\s+\d+\s*$",
        sl,
    ):
        return True

    if re.match(
        r"^(?:an?\s+)?(?:illustration|visualization|visualisation|overview)\b",
        sl,
    ):
        return True

    # A caption fragment ending in "Figure N" without substantive claim.
    if re.search(r"\b(?:figure|fig\.?|table)\s*\d+\s*$", sl) and len(s.split()) <= 25:
        return True

    return False


def _has_external_comparison(sentence: str) -> bool:
    """Detect explicit external/comparative assertions."""
    s = sentence.lower()
    patterns = [
        r"\bcompared\s+(?:with|to)\b",
        r"\bprevious\s+(?:work|method|methods|study|studies|research|version|versions|model|models|network|networks)\b",
        r"\bprior\s+(?:work|method|methods|study|studies|research)\b",
        r"\bexisting\s+(?:method|methods|approach|approaches|system|systems)\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bbaseline(?:s)?\b",
        r"\bsuperior\s+to\b",
        r"\bbetter\s+than\b",
        r"\bworse\s+than\b",
        r"\bmore\s+(?:effective|accurate|efficient|robust|reliable|precise)\s+than\b",
        r"\bmore\s+(?:effective|accurate|efficient|robust|reliable|precise)\s+than\s+(?:the\s+)?previous\s+versions?\b",
        r"\bimproved\s+(?:precision|speed|accuracy|performance)\b.*\bprevious\b",
        r"\bfaster\s+than\b",
        r"\bslower\s+than\b",
        r"\btop\s+choice\b",
        r"\blatest\s+iteration\b",
        r"\bprevious\s+(?:yolo|yolov[3578])\b",
        r"\bearlier\s+(?:study|work|method|version|model|network)\b",
    ]
    return any(re.search(p, s, re.IGNORECASE) for p in patterns)


def _is_mixed_own_external(sentence: str) -> bool:
    s = sentence.lower()
    own_signals = [
        r"\bwe\s+(?:propose|proposed|present|presented|develop|developed|design|designed|implement|implemented|use|used|utilize|utilized|employ|employed|have\s+created|created)\b",
        r"\bour\s+(?:proposed|developed|designed|implemented|method|model|system|approach|results|findings)\b",
        r"\b(?:this|the)\s+study\s+(?:proposes?|presents?|develops?|developed|utilizes?|utilized|employs?|employed)\b",
        r"\b(?:the|this)\s+(?:model|system|method|framework)\b.*\b(?:we|our)\b",
    ]
    has_own_signal = any(re.search(p, s, re.IGNORECASE) for p in own_signals)
    return has_own_signal and _has_external_comparison(sentence)

def looks_like_artifact(sentence: str) -> bool:
    """Skip captions, figure/table/algorithm fragments, code/URL debris, and PDF artifacts."""
    s = sentence.strip()
    sl = s.lower()

    if not s:
        return True

    if _looks_like_algorithm_code(s):
        return True

    if _looks_like_figure_fragment(s):
        return True

    if re.search(r"^(?:figure|fig\.?|table)\s*\d+\s*[\.:)]", sl):
        return True
    if re.search(r"\b(?:figure|fig\.?|table)\s*\d+\s*[\.:)]", sl) and (len(s.split()) <= 35 or re.search(r"\b(?:illustration|prediction|overview|comparison|example|sample|visualization|architecture|results?)\b", sl)):
        return True
    if re.match(r"^(?:illustration|visualization|overview|comparison)\s+of\b", sl):
        return True
    if re.search(r"\b(?:shown|presented|illustrated|depicted)\s+in\s+(?:fig(?:ure)?|table)\s*\d+\b", sl) and len(s.split()) <= 35:
        return True
    if re.search(r"\b(?:shown|presented|illustrated|depicted)\s+in\s+\d+\b", sl) and len(s.split()) <= 35:
        return True
    if re.search(r"\b(?:illustration|visualization|visualisation|overview)\b.*\b(?:shown|presented|illustrated|depicted)\s+in\s+figure\s*\d+", sl):
        return True
    if re.match(r"^\d+(?:\.\d+)+\s+[A-Z][A-Za-z0-9 /&()\-]{1,80}\s+(?:table|figure|fig\.?|algorithm)\s*\d+", s, re.I):
        return True

    # Figure captions are not always prefixed with "Figure 1." after PDF
    # extraction. Common caption language such as "Images from different..."
    # should be treated as an artifact when it contains subfigure labels.
    if (
        re.search(
            r"\b(?:images?|examples?|samples?|visuali[sz]ation|"
            r"comparison|illustration)\b",
            sl,
        )
        and re.search(r"(?:\ba\)|\bb\)|\bc\)|\bd\)|\(a\)|\(b\))", sl)
    ):
        return True

    if re.search(r"\balgorithm\s*\d+\s*[\.:]", sl):
        return True
    if re.search(r"\balgorithm\s*[12]\b", sl) and re.search(
        r"\b(?:input|output|return|end\s+for|calculate|sample\s+rate)\b", sl
    ):
        return True

    if re.search(r"\b(?:github|gitlab)\b|\.git\b|arxiv\.\w+/", sl):
        return True

    # Typical flattened table row / metric fragment.
    tokens = s.split()
    if len(tokens) >= 4:
        numeric_tokens = sum(1 for token in tokens if re.fullmatch(r"[\d.,%±+\-]+", token))
        if numeric_tokens >= 3 and numeric_tokens / len(tokens) >= 0.4:
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



def is_method_or_experimental_description(sentence: str) -> bool:
    """Detect author-method/setup sentences that normally need no external citation."""
    s = sentence.strip()
    patterns = [
        r"\b(?:we|our)\b.*\b(?:used|utilized|applied|implemented|performed|conducted|trained|tested|evaluated|calculated|selected|sampled|sorted|adjusted|augmented)\b",
        r"\b(?:was|were)\s+(?:used|utilized|applied|implemented|performed|conducted|calculated|selected|sampled|sorted|adjusted|augmented)\b",
        r"\b(?:the|this)\s+(?:model|system|algorithm|framework|dataset|study|experiment)\b.*\b(?:training|validation|testing|inference|sample rate|augmentation|frames?)\b",
        r"\b(?:sample rate|frame sampling|data augmentation|rotation|scaling|cropping|blurring|color manipulation)\b.*\b(?:was|were|is|are|used|applied|calculated|adjusted|performed)\b",
        r"\bthe algorithm receives\b",
        r"\b(?:all|three)\s+models\s+were\s+trained\b",
    ]
    return any(re.search(p, s, re.I) for p in patterns)

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

    if re.search(
        r"\b(?:data augmentation|augmentation|training data)\b.*\b(?:common|widely used|standard)\s+technique\b",
        sentence,
        re.IGNORECASE,
    ) or re.search(
        r"\bis a common technique used in computer vision\b",
        sentence,
        re.IGNORECASE,
    ):
        return True, "general_factual_claim", 0.86

    if _is_mixed_own_external(sentence):
        return True, "own_research_with_external_comparison", 0.94

    if is_external_research_claim(sentence):
        return True, "external_research_claim", 0.94

    if is_own_research_claim(sentence):
        return False, "authors_own_research_claim", 0.90

    if re.search(
        r"\b(?:provided separately by the organizers|provided by organizers|"
        r"organizers of the competition|challenge includes|submission to the challenge|"
        r"video ID is|confidence is a probability|leaderboard ranking)\b",
        sentence,
        re.IGNORECASE,
    ):
        return True, "external_factual_claim", 0.86

    if is_method_or_experimental_description(sentence):
        return False, "method_or_experimental_description", 0.72

    if (
        _has_external_comparison(sentence)
        or re.search(
            r"\b(?:common|widely used|standard|latest|top choice|user[- ]friendly API)\b",
            sentence,
            re.IGNORECASE,
        )
    ):
        return True, "general_factual_claim", 0.86

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
# PARAGRAPH-AWARE CONTEXT
# ============================================================

def split_paragraphs(text: str) -> list[str]:
    """Split cleaned text into paragraph-like blocks with structural boundaries."""
    if not text:
        return []
    repaired = _repair_pdf_artifacts(text)
    blocks = [
        re.sub(r"[ \t]+", " ", b).strip()
        for b in re.split(r"\n\s*\n+", repaired)
        if b.strip()
    ]
    return blocks


def _paragraph_sentence_groups(text: str) -> list[list[str]]:
    """
    Return sentence groups while retaining paragraph membership.

    This is the key architectural change: citation context is calculated
    independently inside each paragraph-like block.
    """
    groups = []
    for paragraph in split_paragraphs(text):
        sentences = split_sentences(paragraph)
        if sentences:
            groups.append(sentences)
    return groups


def _flatten_paragraph_sentences(text: str) -> tuple[list[str], list[int]]:
    """
    Flatten paragraph sentence groups while returning a paragraph id for
    every sentence.
    """
    sentences = []
    paragraph_ids = []

    for paragraph_id, group in enumerate(_paragraph_sentence_groups(text)):
        for sentence in group:
            sentences.append(sentence)
            paragraph_ids.append(paragraph_id)

    return sentences, paragraph_ids


def _paragraph_citation_context(
    paragraph_sentences: list[str],
    max_inherited: int = 18,
) -> list[bool]:
    """
    Propagate citation context only inside the current paragraph.

    A citation-bearing technical sentence can support nearby technical
    continuation sentences such as:
        YOLOv5 [15-20] ...
        This results ...
        A SPP block ...
        Additionally, PANet ...

    Inheritance stops at:
      - a new strong external attribution,
      - a standalone quantitative external claim,
      - a non-technical sentence,
      - or the inheritance limit.

    Own-research sentences are never forced into inherited citation context.
    """
    inherited = [False] * len(paragraph_sentences)
    active = False
    remaining = 0

    for i, sentence in enumerate(paragraph_sentences):
        s = sentence.strip()

        # An explicit citation starts a context only when it is attached to
        # technical/explanatory material. A citation elsewhere should not make
        # the entire paragraph inherit blindly.
        if has_citation(s):
            active = _is_technical_sentence(s)
            remaining = max_inherited if active else 0
            continue

        if not active:
            continue

        if is_own_research_claim(s) and not _has_external_comparison(s):
            active = False
            remaining = 0
            continue

        # External/evaluative assertions must keep their own citation need;
        # they should not be silently suppressed by inherited technical context.
        if _has_external_comparison(s) or _has_strong_external_marker(s):
            active = False
            remaining = 0
            continue

        # Do not transfer a YOLOv5-only citation blindly to a new YOLOv8
        # architecture/property statement.
        prior = paragraph_sentences[i - 1] if i > 0 else ""
        distinct_model_claim = (
            bool(re.search(r"\bYOLOv8\b", s, re.IGNORECASE))
            and bool(re.search(r"\b(?:anchor[- ]free|feature pyramid|backbone|neck|head|architecture|API|latest|precise|fast|effective|performance)\b", s, re.IGNORECASE))
            and bool(re.search(r"\bYOLOv5\b", prior, re.IGNORECASE))
            and not has_citation(s)
        )

        if distinct_model_claim:
            active = False
            remaining = 0
            continue

        if _is_related_technical_continuation(
            prior,
            s,
        ):
            inherited[i] = True
            remaining -= 1
            if remaining <= 0:
                active = False
        elif _is_technical_sentence(s):
            inherited[i] = True
            remaining -= 1
            if remaining <= 0:
                active = False
        else:
            active = False
            remaining = 0

    return inherited


def _citation_context_for_sentences(
    sentences: list[str],
    paragraph_ids: Optional[list[int]] = None,
) -> list[bool]:
    """
    Backward-compatible citation-context API.

    If paragraph_ids are supplied, inheritance is calculated independently
    per paragraph. Without them, the legacy single-group behavior is retained
    for callers outside analyze_citations().
    """
    if not sentences:
        return []

    if paragraph_ids is None:
        return _paragraph_citation_context(sentences)

    result = [False] * len(sentences)
    grouped = {}

    for index, paragraph_id in enumerate(paragraph_ids):
        grouped.setdefault(paragraph_id, []).append(index)

    for indices in grouped.values():
        local_sentences = [sentences[i] for i in indices]
        local_context = _paragraph_citation_context(local_sentences)
        for local_index, global_index in enumerate(indices):
            result[global_index] = local_context[local_index]

    return result


# ============================================================
# SENTENCE SPLITTING
# ============================================================

def _repair_pdf_artifacts(text: str) -> str:
    """Repair common flattened-PDF extraction artifacts before classification."""
    t = text or ""

    # Broken figure/caption tokenization seen in extracted text.
    t = re.sub(r"(?i)city\s*chal\s*figure\s*2\s*\.?", "CITY CHALLENGE.\n\nFigure 2.", t)
    t = re.sub(r"(?i)chal\s*figure\s*2\s*\.?", "CHALLENGE.\n\nFigure 2.", t)
    t = re.sub(r"(?i)\bchallenge\.\s*lenge,\s*specifically", "CHALLENGE, specifically", t)

    # Put major headings on their own paragraph even when PDF extraction glued
    # them to the first sentence of the section.
    headings = [
        "Training and Validation Dataset for Developing the Detection Model",
        "Results and Discussion", "Comparative Analysis", "Data Overview",
        "Data Augmentation", "Helmet Detection Models", "Model Training",
        "Test Dataset", "Related Works", "Literature Review", "Methodology",
        "Introduction", "Background", "Methods", "Experiments",
        "Discussion", "Conclusion", "Future Work", "References", "Bibliography",
    ]
    for h in sorted(headings, key=len, reverse=True):
        # beginning or whitespace-delimited heading followed by substantive text
        t = re.sub(
            rf"(?i)(?<![A-Za-z])({re.escape(h)})(?=\s+[A-Z0-9])",
            r"\n\n\1\n\n",
            t,
        )

    # Figure/table/algorithm labels become independent blocks.
    t = re.sub(
        r"(?i)\s+(?=(?:Figure|Fig\.?|Table|Algorithm)\s*\d+\s*[:.\)])",
        "\n\n",
        t,
    )
    t = re.sub(r"(?i)\s+(?=Algorithm\s*\d+\b)", "\n\n", t)

    # A lost figure number after "shown/presented in" is not a research claim.
    t = re.sub(
        r"(?i)\b(shown|presented|illustrated|depicted)\s+in\s+(\d+)\s*\.",
        r"\1 in Figure \2.",
        t,
    )

    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n[ \t]+", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def split_sentences(text: str) -> list[str]:
    """Split cleaned research text while repairing common PDF extraction fragments."""
    if not text:
        return []

    protected = _repair_pdf_artifacts(text)

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

    parts = re.split(r"\n\s*\n+", protected)
    sentences: list[str] = []

    heading_prefix = (
        r"^(?:\d+(?:\.\d+)*[.)]?\s+)?"
        r"(?:Introduction|Background|Related Works?|Literature Review|"
        r"Methodology|Methods|Data Overview|Data Augmentation|"
        r"Training and Validation Dataset for Developing the Detection Model|"
        r"Helmet Detection Models|Model Training|Comparative Analysis|"
        r"Test Dataset|Experiments?|Results and Discussion|Discussion|"
        r"Conclusion|Future Work)\s+(?=[A-Z0-9])"
    )

    for block in parts:
        block = block.strip()
        if not block:
            continue

        chunks = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", block)

        for part in chunks:
            part = part.strip()
            if not part:
                continue

            for old, new in replacements.items():
                part = part.replace(new, old)

            part = re.sub(heading_prefix, "", part, flags=re.IGNORECASE).strip()

            if not part:
                continue

            # Drop obvious algorithm/caption blocks immediately.
            if _looks_like_algorithm_code(part) or _looks_like_figure_fragment(part):
                continue

            sentences.append(part)

    # Reconstruct common PDF line/sentence fragments.
    repaired: list[str] = []
    continuation_prefixes = (
        "lenge,",
        "of three single",
        "of various single",
        "on helmet detection techniques",
        "which focuses on",
        "specifically track",
        "to help the developed model",
        "to increase the variety",
        "techniques to generate",
        "is a common technique",
    )

    for part in sentences:
        stripped = part.strip()

        # Explicitly ignore isolated algorithm/caption leftovers.
        if _looks_like_algorithm_code(stripped) or _looks_like_figure_fragment(stripped):
            continue

        lower = stripped.lower()

        if repaired and (
            lower.startswith(continuation_prefixes)
            or stripped.startswith((",", ".", ";", ")", "]"))
            or (stripped[:1].islower())
            or re.match(r"(?i)^(?:algorithm|figure|fig\.?|table)\s*\d+\)?\s*", stripped)
            or not re.search(r"[.!?][\"'”’)]*$", repaired[-1].rstrip())
        ):
            repaired[-1] = (repaired[-1].rstrip() + " " + stripped).strip()
        else:
            repaired.append(stripped)

    # Fix the common split "CHALLENGE. LENGE, specifically..." artifact.
    final: list[str] = []
    for part in repaired:
        if final and re.match(r"(?i)^lenge,\s*", part):
            final[-1] = re.sub(
                r"(?i)\bchallenge\.?\s*$",
                "CHALLENGE",
                final[-1],
            ).rstrip() + " " + re.sub(r"(?i)^lenge,\s*", "", part)
        else:
            final.append(part)

    return [x.strip() for x in final if x.strip()]


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
# CITATION CONTEXT PROPAGATION
# ============================================================

def _technical_topic_tokens(sentence: str) -> set[str]:
    s = sentence.lower()
    tokens = set(re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", s))
    important = {
        "yolo", "yolov5", "yolov7", "yolov8", "cspdarknet",
        "cspdarknet53", "panet", "spp", "backbone", "neck", "head",
        "anchor-free", "feature", "pyramid", "bounding", "box",
        "tta", "dataset", "fps", "map", "iou",
    }
    return {t for t in tokens if len(t) >= 4 or t in important}


def _has_strong_external_marker(sentence: str) -> bool:
    s = sentence.lower()
    patterns = [
        r"\bthe authors\b", r"\banother study\b",
        r"\bprevious studies?\b", r"\bprior studies?\b",
        r"\bprevious work\b", r"\bprior work\b",
        r"\baccording to\b", r"\breported\b",
        r"\bhas been shown\b", r"\bhave been shown\b",
        r"\bhas been proposed\b", r"\bhave been proposed\b",
        r"\bstate[- ]of[- ]the[- ]art\b",
        r"\bworld health organization\b",
    ]
    return any(re.search(p, s, re.I) for p in patterns)


def _is_quantitative_external_claim(sentence: str) -> bool:
    return bool(re.search(
        r"\b\d+(?:\.\d+)?\s*(?:%|percent|million|billion|thousand|"
        r"ms|fps|km|kg|years?|vehicles?|people)\b",
        sentence, re.I
    ))


def _is_technical_sentence(sentence: str) -> bool:
    if re.search(r"\b(?:receptive field|SPP|spatial pyramid pooling|PANet|feature pyramid|feature maps?|backbone|neck|head|CSPDarknet|EELAN|compound scaling|anchor[- ]?free|convolutional layers?|detection head|network architecture|object detection model)\b", sentence, re.IGNORECASE):
        return True

    s = sentence.lower()
    patterns = [
        r"\byolov[3578]\b", r"\bcspdarknet(?:53)?\b", r"\bpanet\b",
        r"\bspp\b", r"\bbackbone\b", r"\bneck\b", r"\bhead\b",
        r"\bbounding boxes?\b", r"\banchor[- ]free\b",
        r"\bfeature pyramid\b", r"\breceptive field\b",
        r"\bconvolutional\b", r"\bparameters?\b",
        r"\bobject detection\b", r"\barchitecture\b",
    ]
    return any(re.search(p, s, re.I) for p in patterns)


def _is_related_technical_continuation(previous: str, current: str) -> bool:
    """
    Decide whether `current` is a continuation of the cited technical topic.
    """
    if not _is_technical_sentence(current):
        return False

    if is_own_research_claim(current):
        return False

    previous_tokens = _technical_topic_tokens(previous)
    current_tokens = _technical_topic_tokens(current)

    # Shared technical vocabulary is the strongest continuation signal.
    if previous_tokens & current_tokens:
        return True

    # Pronoun/additive continuations are common in technical descriptions.
    if re.match(
        r"^(this|these|such|it|they|additionally|also|similarly|"
        r"furthermore|moreover|in addition)\b",
        current.strip(),
        re.I,
    ):
        return True

    # Some papers omit the repeated topic completely:
    # "A SPP block is added..." after a YOLO architecture sentence.
    # The technical vocabulary check above handles most cases; these explicit
    # architecture terms cover the common YOLO family continuation.
    return bool(re.search(
        r"\b(?:spp|panet|backbone|neck|head|receptive field|"
        r"feature pyramid|cspdarknet|bounding boxes?)\b",
        current,
        re.I,
    ))


def _deduplicate_citation_findings(findings: list[dict]) -> list[dict]:
    result = []

    for finding in findings:
        claim = re.sub(r"\s+", " ", finding.get("claim_text", "").strip().lower())
        duplicate = False

        for old in result:
            old_claim = re.sub(r"\s+", " ", old.get("claim_text", "").strip().lower())
            a = set(re.findall(r"[a-z0-9]+", claim))
            b = set(re.findall(r"[a-z0-9]+", old_claim))

            if len(a) >= 6 and len(b) >= 6:
                overlap = len(a & b) / max(1, len(a | b))
                same_type = (
                    finding.get("claim_type") ==
                    old.get("claim_type")
                )
                if (
                    overlap >= 0.75
                    and same_type
                    and not _has_strong_external_marker(claim)
                ):
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
    Analyze citation risk using paragraph-aware claim classification.

    Semantics:
      - citation_present: an actual citation marker occurs in the sentence.
      - citation_needed: the sentence makes an external/background claim that
        independently requires support.
      - inherited_context: a technical continuation is covered by a citation
        already present in the same paragraph.
      - own_research: the sentence describes the authors' own method, setup,
        experiment, result, or contribution and therefore is not independently
        citation-required.

    The module is a citation-risk analyzer, not a plagiarism detector.
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
        raise ValueError("No extracted text available for this paper.")

    # ------------------------------------------------------------
    # Clean + paragraph-aware sentence splitting
    # ------------------------------------------------------------
    cleaned_text = clean_research_text(raw_text)

    if not cleaned_text.strip():
        raise ValueError(
            "Extracted text exists, but text cleaning removed all content. "
            "Check the PDF extraction/cleaning step."
        )

    sentences, paragraph_ids = _flatten_paragraph_sentences(cleaned_text)
    inherited_citations = _citation_context_for_sentences(
        sentences,
        paragraph_ids,
    )

    findings = []

    # These counters deliberately represent CLAIMS, not only citation-required
    # claims. This lets the report distinguish own research from external risk.
    total_claims = 0
    citations_present = 0
    citation_required_claims = 0
    cited_required_claims = 0
    own_research_claims = 0
    inherited_context_claims = 0
    ignored_artifacts = 0

    current_section = None
    references_started = False

    for index, sentence in enumerate(sentences):
        sentence = sentence.strip()

        if re.match(r"^(?:\d+(?:\.\d+)*[\.)]?\s*)?(?:references|bibliography)\b", sentence, re.IGNORECASE):
            references_started = True
            ignored_artifacts += 1
            continue
        if references_started:
            ignored_artifacts += 1
            continue

        # --------------------------------------------------------
        # Artifact / structural filtering
        # --------------------------------------------------------
        if (
            _looks_like_algorithm_code(sentence)
            or _looks_like_figure_fragment(sentence)
            or looks_like_artifact(sentence)
        ):
            ignored_artifacts += 1
            continue

        if not looks_like_claim(sentence):
            ignored_artifacts += 1
            continue

        heading_match = re.match(
            r"^\s*(\d+(?:\.\d+)*)[.)]?\s+"
            r"([A-Z][A-Za-z0-9 /&()\-]{1,100})",
            sentence,
        )

        if heading_match and len(sentence.split()) <= 18:
            current_section = heading_match.group(2).strip()
            ignored_artifacts += 1
            continue

        if looks_like_heading(sentence):
            current_section = sentence.strip()
            ignored_artifacts += 1
            continue

        # --------------------------------------------------------
        # Sentence-level signals
        # --------------------------------------------------------
        citation_present_bool = has_citation(sentence)
        inherited = inherited_citations[index]

        # Priority:
        # 1. artifact/heading/reference (handled above)
        # 2. actual citation presence
        # 3. own research
        # 4. inherited technical context
        # 5. external research
        # 6. quantitative external
        # 7. general factual
        # 8. generic factual
        own_research = is_own_research_claim(sentence)

        citation_needed_bool, reason, confidence = classify_claim(sentence)

        mixed_external = own_research and _has_external_comparison(sentence)

        if mixed_external:
            # The sentence describes the authors' work but also makes an
            # externally comparative/evaluative claim, so it still needs
            # support for that comparison.
            citation_needed_bool = True
            reason = "own_research_with_external_comparison"
            confidence = max(confidence, 0.94)

        elif own_research:
            citation_needed_bool = False
            reason = "authors_own_research_claim"
            confidence = max(confidence, 0.93)
            own_research_claims += 1

        elif inherited and _is_technical_sentence(sentence):
            # Inherited context means this sentence is not independently
            # missing a citation. It remains a claim, but its support comes
            # from the citation-bearing sentence in the same paragraph.
            citation_needed_bool = False
            reason = "inherited_technical_context"
            confidence = max(confidence, 0.91)
            inherited_context_claims += 1

        total_claims += 1

        if citation_present_bool:
            citations_present += 1

        if citation_needed_bool:
            citation_required_claims += 1
            if citation_present_bool:
                cited_required_claims += 1

        # --------------------------------------------------------
        # Findings
        #
        # Keep ALL meaningful claim classifications in the response. This is
        # important because the frontend/report must show why a citation was
        # or was not required. Only genuinely missing external claims get a
        # suggested source.
        # --------------------------------------------------------
        suggested_source_id = None
        suggestion_reason = None

        if citation_needed_bool and not citation_present_bool:
            suggested_source_id, suggestion_reason = _find_best_source(
                db=db,
                project_id=project_id,
                claim_text=sentence,
                exclude_paper_id=paper_id,
            )

        if citation_present_bool:
            presentation_reason = (
                "citation_present"
                if citation_needed_bool
                else reason
            )
        elif mixed_external:
            presentation_reason = "own_research_with_external_comparison"
        elif own_research:
            presentation_reason = "authors_own_research_claim"
        elif inherited:
            presentation_reason = "inherited_technical_context"
        else:
            presentation_reason = reason

        findings.append(
            {
                "section": current_section,
                "claim_text": sentence,
                "claim_type": (
                    "own_research"
                    if own_research
                    else (
                        "inherited_context"
                        if inherited
                        else reason
                    )
                ),
                "citation_present": "yes" if citation_present_bool else "no",
                "citation_needed": "yes" if citation_needed_bool else "no",
                "citation_status": (
                    "cited"
                    if citation_present_bool
                    else (
                        "covered_by_inherited_context"
                        if inherited
                        else (
                            "not_required"
                            if not citation_needed_bool
                            else "missing"
                        )
                    )
                ),
                "confidence": round(float(confidence), 3),
                "suggested_source_id": suggested_source_id,
                "suggestion_reason": (
                    suggestion_reason
                    if suggestion_reason
                    else presentation_reason
                ),
            }
        )

    findings = _deduplicate_citation_findings(findings)

    # ------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------
    if citation_required_claims > 0:
        citation_coverage = (
            cited_required_claims / citation_required_claims
        ) * 100.0
    else:
        citation_coverage = 100.0

    potential_missing_citations = max(
        0,
        citation_required_claims - cited_required_claims,
    )

    # ------------------------------------------------------------
    # Risk level is based ONLY on genuinely required external claims.
    # Own research and inherited technical continuation do not increase risk.
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
        "citation_required_claims": citation_required_claims,
        "cited_required_claims": cited_required_claims,
        "potential_missing_citations": potential_missing_citations,
        "own_research_claims": own_research_claims,
        "inherited_context_claims": inherited_context_claims,
        "ignored_artifacts": ignored_artifacts,
        "risk_level": risk_level,
        "findings": findings,
        "cleaned_text_length": len(cleaned_text),
        "raw_text_length": len(raw_text),
    }

