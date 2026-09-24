from pydantic import BaseModel
from typing import List


class ImprovementRequest(BaseModel):
    manuscript: str = ""


class ImprovementResponse(BaseModel):
    project_id: int
    paper_id: int

    overall_plan: str

    priority_actions: List[dict]

    section_improvements: List[dict]

    methodology_improvements: List[str]

    experiment_improvements: List[str]

    writing_improvements: List[str]

    citation_improvements: List[str]

    formatting_improvements: List[str]

    quick_fixes: List[str]

    long_term_improvements: List[str]

    revised_structure: List[str]

    implementation_order: List[str]