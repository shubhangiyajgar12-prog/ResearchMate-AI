from fastapi import APIRouter, HTTPException

from app.schemas.discovery.topic import (
    TopicValidationRequest,
    TopicValidationResponse,
)

from app.services.discovery.topic_validation import validate_topic


router = APIRouter(
    prefix="/discovery",
    tags=["Research Discovery"],
)


@router.post(
    "/topic-validation",
    response_model=TopicValidationResponse,
)
def topic_validation(
    request: TopicValidationRequest,
):
    """
    Validate a research topic and return:
    - detected research field
    - topic specificity
    - feasibility indication
    - extracted keywords
    - validation summary
    """

    try:
        topic = request.topic.strip()

        if not topic:
            raise HTTPException(
                status_code=400,
                detail="Research topic cannot be empty.",
            )

        result = validate_topic(topic)

        if not result:
            raise HTTPException(
                status_code=502,
                detail="Topic validation service returned no result.",
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Topic validation failed: {str(exc)}",
        ) from exc