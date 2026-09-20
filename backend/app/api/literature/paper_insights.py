from fastapi import APIRouter, HTTPException

from app.schemas.literature.paper_insights import (
    PaperInsightsRequest,
    PaperInsightsResponse,
)

from app.services.literature.paper_insights import (
    generate_insights,
)


router = APIRouter(
    prefix="/literature",
    tags=["Literature Intelligence"]
)


@router.post(
    "/paper-insights",
    response_model=PaperInsightsResponse
)
def generate_paper_insights(
    request: PaperInsightsRequest
):
    try:
        data = request.model_dump()

        result = generate_insights(data)

        return result

    except Exception as error:
        print("\n" + "=" * 70)
        print("PAPER INSIGHTS ERROR")
        print("=" * 70)
        print(type(error).__name__)
        print(str(error))
        print("=" * 70 + "\n")

        raise HTTPException(
            status_code=500,
            detail=f"Paper insights generation failed: {str(error)}"
        )