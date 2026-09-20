from typing import Any, Dict

from app.schemas.literature.paper_insights import (
    PaperInsightsResponse,
)

from app.services.ai.llm_service import (
    generate_structured_response,
)


def build_paper_context(data: Dict[str, Any]) -> str:
    """
    Converts extracted paper information into a structured
    context for AI analysis.
    """

    sections = []

    if data.get("title"):
        sections.append(
            f"TITLE:\n{data['title']}"
        )

    if data.get("abstract"):
        sections.append(
            f"ABSTRACT:\n{data['abstract']}"
        )

    if data.get("methodology"):
        sections.append(
            f"METHODOLOGY:\n{data['methodology']}"
        )

    if data.get("dataset"):
        sections.append(
            f"DATASET:\n{data['dataset']}"
        )

    if data.get("results"):
        sections.append(
            f"RESULTS:\n{data['results']}"
        )

    if data.get("key_findings"):
        findings = "\n".join(
            f"- {finding}"
            for finding in data["key_findings"]
        )

        sections.append(
            f"KEY FINDINGS:\n{findings}"
        )

    if data.get("limitations"):
        sections.append(
            f"REPORTED LIMITATIONS:\n{data['limitations']}"
        )

    if data.get("future_work"):
        sections.append(
            f"REPORTED FUTURE WORK:\n{data['future_work']}"
        )

    return "\n\n".join(sections)


def generate_insights(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates AI-powered research insights using Gemini.
    """

    paper_context = build_paper_context(data)

    prompt = f"""
You are ResearchMate AI, an academic research mentor.

Analyze the following research paper information.

Generate the following:

1. Research problem
2. Research objective
3. Methodology summary
4. Key contributions
5. Research gaps
6. Limitations
7. Novelty indicators
8. Possible improvements
9. Future research directions

IMPORTANT RULES:

- Use only information supported by the provided paper content.
- Do not invent facts.
- Clearly distinguish explicit statements from reasonable
  research-oriented interpretations.
- If a limitation is not explicitly stated, identify it only
  as a potential limitation.
- If future work is not explicitly stated, identify potential
  future research directions based on the reported work.
- Do not claim something is novel simply because it sounds
  interesting.
- Make research gaps specific and useful.
- Keep the analysis concise but meaningful.

PAPER INFORMATION:

{paper_context}
"""

    result = generate_structured_response(
        prompt=prompt,
        response_schema=PaperInsightsResponse,
    )

    return result.model_dump()