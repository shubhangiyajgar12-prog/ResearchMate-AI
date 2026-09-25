from fastapi import APIRouter

from app.schemas.discovery.topic import (
    TopicValidationRequest,
    TopicValidationResponse
)

from app.schemas.discovery.novelty import (
    NoveltyAnalysisRequest,
    NoveltyAnalysisResponse
)
from app.schemas.discovery.feasibility import (
    FeasibilityAnalysisRequest,
    FeasibilityAnalysisResponse
)
from app.services.discovery.feasibility import (
    analyze_feasibility
)
from app.schemas.discovery.research_questions import (
    ResearchQuestionRequest,
    ResearchQuestionResponse
)
from app.services.discovery.research_questions import (
    generate_research_questions
)
from app.schemas.discovery.research_gap import (
    ResearchGapRequest,
    ResearchGapResponse
)

from app.services.discovery.topic_validation import (
    validate_topic
)

from app.services.discovery.novelty_analysis import (
    analyze_novelty
)

from app.services.discovery.research_gap import (
    analyze_research_gap
)

from app.services.discovery.evidence_analysis import (
    analyze_topic_with_evidence
)


router = APIRouter(
    prefix="/discovery",
    tags=["Research Discovery"]
)


# ==================================================
# TOPIC VALIDATION
# ==================================================

@router.post(
    "/topic-validation",
    response_model=TopicValidationResponse
)
def topic_validation(
    request: TopicValidationRequest
):
    return validate_topic(request.topic)


# ==================================================
# NOVELTY ANALYSIS
# ==================================================

@router.post(
    "/novelty-analysis",
    response_model=NoveltyAnalysisResponse
)
def novelty_analysis(
    request: NoveltyAnalysisRequest
):
    return analyze_novelty(request.topic)


# ==================================================
# RESEARCH GAP ANALYSIS
# ==================================================

@router.post(
    "/research-gap",
    response_model=ResearchGapResponse
)
def research_gap(
    request: ResearchGapRequest
):
    return analyze_research_gap(request.topic)
# ==================================================
# RESEARCH QUESTIONS + HYPOTHESIS
# ==================================================

@router.post(
    "/research-questions",
    response_model=ResearchQuestionResponse
)
def research_questions(
    request: ResearchQuestionRequest
):

    result = generate_research_questions(
        request.topic,
        request.research_gaps
    )

    return result
# ==================================================
# FEASIBILITY ANALYSIS
# ==================================================

@router.post(
    "/feasibility",
    response_model=FeasibilityAnalysisResponse
)
def feasibility_analysis(
    request: FeasibilityAnalysisRequest
):

    result = analyze_feasibility(
        request.topic
    )

    return result

# ==================================================
# CONSOLIDATED EVIDENCE-FIRST ANALYSIS
# ==================================================

@router.post(
    "/analyze"
)
def analyze_discovery(
    request: TopicValidationRequest
):
    """
    Run one evidence snapshot for the complete Discovery page.

    Using one consolidated call keeps specificity, prior-art, gap,
    questions, feasibility and literature evidence internally consistent.
    """
    return analyze_topic_with_evidence(request.topic)

