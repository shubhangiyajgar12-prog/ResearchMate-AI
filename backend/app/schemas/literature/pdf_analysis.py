from pydantic import BaseModel, Field
from typing import List


class DatasetAnalysis(BaseModel):
    training_videos: str | None = None
    testing_videos: str | None = None
    video_duration: str | None = None
    frame_rate: str | None = None
    resolution: str | None = None
    training_examples: str | None = None
    train_split: str | None = None
    validation_split: str | None = None
    test_split: str | None = None
    positive_examples: str | None = None
    negative_examples: str | None = None
    testing_examples: str | None = None
    augmentation: List[str] = Field(default_factory=list)
    processing: List[str] = Field(default_factory=list)


class MethodologySubsection(BaseModel):
    number: str
    title: str
    text: str


class TrainingDetails(BaseModel):
    epochs: str | None = None
    batch_size: str | None = None
    image_size: str | None = None
    optimizer: str | None = None
    learning_rate: str | None = None


class MethodologyAnalysis(BaseModel):
    subsections: List[MethodologySubsection] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)
    training: TrainingDetails = Field(default_factory=TrainingDetails)
    test_time_augmentation: bool = False


class ValidationResults(BaseModel):
    map_50: float | None = None
    map_50_95: float | None = None
    precision: float | None = None
    recall: float | None = None
    reported_map: float | None = None


class TestResults(BaseModel):
    map: float | None = None
    fps: int | None = None


class ValidationModelResult(BaseModel):
    model: str
    values: List[float] = Field(default_factory=list)


class TestModelResult(BaseModel):
    model: str
    values: List[float] = Field(default_factory=list)


class ResultsAnalysis(BaseModel):
    validation: ValidationResults = Field(default_factory=ValidationResults)
    test: TestResults = Field(default_factory=TestResults)
    validation_models: List[ValidationModelResult] = Field(default_factory=list)
    test_models: List[TestModelResult] = Field(default_factory=list)
    challenge_rank: int | None = None
    best_model: str | None = None


class PDFAnalysisResponse(BaseModel):
    filename: str
    page_count: int
    extracted_text_length: int
    extracted_text: str | None = None

    title: str | None = None
    abstract: str | None = None

    methodology: MethodologyAnalysis = Field(default_factory=MethodologyAnalysis)
    dataset: DatasetAnalysis = Field(default_factory=DatasetAnalysis)
    results: ResultsAnalysis = Field(default_factory=ResultsAnalysis)

    limitations: str | None = None
    future_work: str | None = None
    conclusion: str | None = None

    key_findings: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    subsections: List[MethodologySubsection] = Field(default_factory=list)
