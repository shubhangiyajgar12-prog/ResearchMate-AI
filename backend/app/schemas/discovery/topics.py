from fastapi import APIRouter

from app.schemas.discovery.topic import (
    TopicValidationRequest,
    TopicValidationResponse
)

from app.services.discovery.topic_validation import validate_topic


router = APIRouter(
    prefix="/discovery",
    tags=["Research Discovery"]
)


@router.post(
    "/topic-validation",
    response_model=TopicValidationResponse
)
def topic_validation(
    request: TopicValidationRequest
):
    result = validate_topic(request.topic)

    return result