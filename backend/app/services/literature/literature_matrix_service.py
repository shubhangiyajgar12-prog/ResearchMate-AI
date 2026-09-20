from typing import Any, Dict, List

from app.schemas.literature.literature_matrix import LiteratureMatrixResponse
from app.services.ai.llm_service import generate_structured_response


def _paper_context(papers: List[Dict[str, Any]]) -> str:
    blocks = []

    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.get("authors") or [])

        blocks.append(
            f"""PAPER {index}
DATABASE_ID: {paper["id"]}
TITLE: {paper.get("title") or ""}
YEAR: {paper.get("year") or ""}
AUTHORS: {authors}
ABSTRACT: {paper.get("abstract") or ""}
"""
        )

    return "\n".join(blocks)


def generate_literature_matrix(
    project_id: int,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = f"""
You are ResearchMate AI, an academic literature-analysis assistant.

Create a literature matrix from the selected research papers below.

For EACH paper, extract or conservatively infer from the supplied abstract/title:
- research_problem
- methodology
- dataset
- key_results
- limitations
- research_gap

Then compare the papers and produce:
- cross_paper_findings
- common_methods
- common_limitations
- potential_research_gaps

IMPORTANT:
1. Use ONLY the supplied paper information.
2. Do not invent datasets, metrics, methods, limitations, or findings.
3. If a field is not supported, write "Not specified in provided information."
4. A research gap must be presented as a potential/open area, not as a proven fact.
5. Do not claim a paper is novel unless the supplied information explicitly supports that claim.
6. Keep each matrix cell concise and useful for a student researcher.
7. Preserve the exact database ID for each paper.

PROJECT ID: {project_id}

SELECTED PAPERS:

{_paper_context(papers)}
"""

    result = generate_structured_response(
        prompt=prompt,
        response_schema=LiteratureMatrixResponse,
    )

    return result.model_dump()
