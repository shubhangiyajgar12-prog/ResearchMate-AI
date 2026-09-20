from typing import Any, Dict, List

from app.schemas.literature.literature_matrix import LiteratureMatrixResponse
from app.services.ai.llm_service import generate_structured_response


def _analysis_value(analysis: Dict[str, Any], key: str) -> str:
    value = analysis.get(key)

    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return str(value)

    return str(value)


def _paper_context(papers: List[Dict[str, Any]]) -> str:
    blocks = []

    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.get("authors") or [])
        analysis = paper.get("analysis") or {}

        blocks.append(
            f"""
PAPER {index}
DATABASE_ID:
{paper["id"]}
TITLE:
{paper.get("title") or ""}
YEAR:
{paper.get("year") or ""}
AUTHORS:
{authors}
ABSTRACT:
{paper.get("abstract") or ""}

PDF ANALYSIS - METHODOLOGY:
{_analysis_value(analysis, "methodology")}

PDF ANALYSIS - DATASET:
{_analysis_value(analysis, "dataset")}

PDF ANALYSIS - RESULTS:
{_analysis_value(analysis, "results")}

PDF ANALYSIS - KEY FINDINGS:
{_analysis_value(analysis, "key_findings")}

PDF ANALYSIS - LIMITATIONS:
{_analysis_value(analysis, "limitations")}

PDF ANALYSIS - FUTURE WORK:
{_analysis_value(analysis, "future_work")}
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

For EACH paper, extract or conservatively infer from the supplied abstract and
PDF analysis:
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
1. Prefer the supplied PDF analysis when it contains more detailed information
   than the abstract.
2. Use ONLY the supplied paper information.
3. Do not invent datasets, metrics, methods, limitations, or findings.
4. If a field is not supported, write: "Not specified in provided information."
5. A research gap must be presented as a potential/open area, not as a proven fact.
6. Do not claim a paper is novel unless the supplied information explicitly supports it.
7. Keep each matrix cell concise and useful for a student researcher.
8. Preserve the exact database ID for each paper.
9. Distinguish reported facts from reasonable research-oriented interpretations.

PROJECT ID:
{project_id}

SELECTED PAPERS:
{_paper_context(papers)}
"""

    result = generate_structured_response(
        prompt=prompt,
        response_schema=LiteratureMatrixResponse,
    )

    return result.model_dump()
