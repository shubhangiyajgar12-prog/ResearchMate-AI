from pydantic import BaseModel, Field
from typing import List


class PaperSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=300)
    limit: int = Field(default=10, ge=1, le=20)


class PaperAuthor(BaseModel):
    name: str


class PaperResult(BaseModel):
    paper_id: str | None = None
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: List[PaperAuthor] = Field(default_factory=list)
    citation_count: int | None = None
    url: str | None = None
    doi: str | None = None


class PaperSearchResponse(BaseModel):
    query: str
    total: int
    papers: List[PaperResult]
    source: str