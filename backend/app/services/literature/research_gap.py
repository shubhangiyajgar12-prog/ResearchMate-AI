from typing import Any, Dict, List

from app.schemas.literature.research_gap import (
    ResearchGapResponse,
)

from app.services.ai.llm_service import (
    generate_structured_response,
)


# ============================================================
# TEXT HELPERS
# ============================================================

def safe_text(value: Any) -> str:
    """
    Convert different data types into clean text.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "; ".join(
            str(item)
            for item in value
        )

    if isinstance(value, dict):
        return str(value)

    return str(value)


# ============================================================
# ANALYSIS EXTRACTION
# ============================================================

def extract_pdf_analysis(
    analysis_json: Any,
) -> Dict[str, Any]:
    """
    Extract useful fields from saved PDF analysis.
    """

    if not isinstance(analysis_json, dict):
        return {
            "methodology": "",
            "dataset": "",
            "results": "",
            "key_findings": [],
            "limitations": "",
            "future_work": "",
            "research_gap": "",
        }

    return {
        "methodology": safe_text(
            analysis_json.get("methodology")
        ),

        "dataset": safe_text(
            analysis_json.get("dataset")
        ),

        "results": safe_text(
            analysis_json.get("results")
        ),

        "key_findings": (
            analysis_json.get("key_findings")
            if isinstance(
                analysis_json.get("key_findings"),
                list,
            )
            else []
        ),

        "limitations": safe_text(
            analysis_json.get("limitations")
        ),

        "future_work": safe_text(
            analysis_json.get("future_work")
        ),

        "research_gap": safe_text(
            analysis_json.get("research_gap")
        ),
    }


# ============================================================
# PAPER CONTEXT
# ============================================================

def build_paper_context(
    papers: List[Dict[str, Any]]
) -> str:
    """
    Build structured context for Gemini.
    """

    blocks = []

    for index, paper in enumerate(
        papers,
        start=1,
    ):

        analysis = paper.get(
            "analysis",
            {},
        )

        pdf_analysis = extract_pdf_analysis(
            analysis
        )

        authors = ", ".join(
            paper.get("authors") or []
        )

        key_findings = "\n".join(
            f"- {finding}"
            for finding in pdf_analysis[
                "key_findings"
            ]
        )

        if not key_findings:
            key_findings = (
                "Not available."
            )

        pdf_status = (
            "Available"
            if paper.get("has_pdf_analysis")
            else "Not available"
        )

        block = f"""
============================================================
PAPER {index}
============================================================

DATABASE PAPER ID:
{paper.get("paper_id")}

TITLE:
{paper.get("title")}

YEAR:
{paper.get("year")}

AUTHORS:
{authors}

PDF ANALYSIS:
{pdf_status}

ABSTRACT:
{paper.get("abstract") or "Not available."}

METHODOLOGY:
{pdf_analysis["methodology"] or "Not available."}

DATASET:
{pdf_analysis["dataset"] or "Not available."}

RESULTS:
{pdf_analysis["results"] or "Not available."}

KEY FINDINGS:
{key_findings}

REPORTED LIMITATIONS:
{pdf_analysis["limitations"] or "Not available."}

REPORTED FUTURE WORK:
{pdf_analysis["future_work"] or "Not available."}

PREVIOUSLY EXTRACTED RESEARCH GAP:
{pdf_analysis["research_gap"] or "Not available."}
"""

        blocks.append(block)

    return "\n".join(blocks)


# ============================================================
# MAIN AI FUNCTION
# ============================================================

def generate_research_gap(
    project_id: int,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:

    paper_context = build_paper_context(
        papers
    )

    prompt = f"""
You are ResearchMate AI, an academic research
mentor specializing in literature analysis.

Your task is to analyze multiple research papers
and identify POTENTIAL research gaps and open
research opportunities.

PROJECT ID:
{project_id}

SELECTED PAPERS:

{paper_context}


============================================================
YOUR TASK
============================================================

Compare the selected papers carefully.

Identify meaningful potential research gaps based on:

1. Research problems
2. Research objectives
3. Methodologies
4. Datasets
5. Experimental settings
6. Results
7. Limitations
8. Future work
9. Differences between approaches
10. Areas that are insufficiently explored across the
    selected papers


============================================================
IMPORTANT ACADEMIC RULES
============================================================

RULE 1:
Do NOT claim that a research gap is proven.

Use wording such as:

- "Potential research gap"
- "Possible open area"
- "The selected studies suggest..."
- "Further investigation may be needed..."

RULE 2:
Use ONLY information provided in the paper context.

Do not invent:

- datasets
- results
- methodologies
- limitations
- citations
- authors
- experimental findings

RULE 3:
If PDF analysis is unavailable for a paper,
use the available title and abstract.

RULE 4:
If evidence is weak, explicitly indicate
lower evidence strength.

RULE 5:
A research gap should connect multiple papers
whenever possible.

RULE 6:
Do not simply summarize papers.

We need COMPARATIVE insights.

RULE 7:
Do not call something "novel" merely because
it appears interesting.

RULE 8:
Affected paper IDs MUST correspond exactly to
the DATABASE PAPER ID values provided.

RULE 9:
Evidence should explain WHY the proposed gap
is suggested.

RULE 10:
Research opportunities should be actionable
and useful for a student researcher.


============================================================
OUTPUT REQUIREMENTS
============================================================

Return:

1. research_gaps

Each research gap must contain:

- gap
- evidence
- affected_papers
- evidence_strength
- research_opportunity


2. cross_paper_patterns

These should describe patterns observed across
the selected studies.

Examples:

- Common methodology
- Similar dataset limitations
- Repeated evaluation limitations
- Different approaches to the same problem
- Missing real-world validation
- Different experimental settings


3. evidence_note

Explain that the gaps are potential/open areas
and require verification using the original papers
and broader literature.


============================================================
QUALITY REQUIREMENTS
============================================================

Generate approximately 2-5 meaningful research gaps
when the evidence supports them.

Avoid generic statements such as:

"More research is needed."

Instead make the gap specific.

For example:

Weak:
"More research is needed on datasets."

Better:
"The selected studies use limited evaluation settings,
suggesting a potential open area in testing the proposed
approaches across more diverse real-world conditions."


Return ONLY the structured response.
"""


    result = generate_structured_response(
        prompt=prompt,
        response_schema=ResearchGapResponse,
    )

    return result.model_dump()