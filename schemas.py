from datetime import datetime
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Geçerli bir e-posta adresi girin")
        return email


class UserCreate(UserCredentials):
    pass


class UserLogin(UserCredentials):
    pass


class UserResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class AnalysisResponse(BaseModel):
    id: int
    filename: str
    summary: str

    model_config = ConfigDict(from_attributes=True)


# ── FAZ 3: Veri Analiz Motoru Response Modelleri ──────────────

class DataAnalysisResponse(BaseModel):
    id: int
    filename: str
    template: str
    row_count: int
    column_count: int
    columns_info: Any       # JSON parse edilmiş sütun bilgileri
    statistics: Any          # JSON parse edilmiş istatistikler
    ai_report: str           # Gemini stratejik rapor
    dataset_id: Optional[int] = None
    analysis_type: str = "dataset"
    status: str = "completed"
    chart_data: list[dict[str, Any]] = Field(default_factory=list)
    quality_issues: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    question: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DataAnalysisListItem(BaseModel):
    id: int
    filename: str
    template: str
    row_count: int
    column_count: int
    question: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CompareResponse(BaseModel):
    file1: str
    file2: str
    ai_report: str


class AskResponse(BaseModel):
    filename: str
    question: str
    answer: str


class SurveyColumnMetadata(BaseModel):
    name: str
    dtype: str
    semantic_type: str
    missing_count: int
    missing_pct: float
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    code_map: dict[str, Any] = Field(default_factory=dict)


class SurveyQuestionItem(BaseModel):
    id: Optional[int] = None
    column_name: str
    question_no: Optional[str] = None
    question_text: str
    question_type: str
    scale_type: Optional[str] = None
    options: dict[str, Any] = Field(default_factory=dict)
    is_likert: bool = False
    is_demographic: bool = False
    is_open_text: bool = False


class SurveyReportItem(BaseModel):
    id: Optional[int] = None
    report_type: str
    status: str
    summary: Any
    metrics: Any
    quality_issues: Any
    ai_report: str
    created_at: Optional[datetime] = None


class SurveyUploadResponse(BaseModel):
    dataset_id: int
    survey_id: int
    filename: str
    title: str
    source_sheet: str
    row_count: int
    column_count: int
    header_row: int
    data_start_row: int
    columns: list[SurveyColumnMetadata]
    questions: list[SurveyQuestionItem]
    report: SurveyReportItem
    created_at: Optional[datetime] = None


class DatasetUploadResponse(BaseModel):
    dataset_id: int
    analysis_id: int
    survey_id: Optional[int] = None
    filename: str
    detected_format: str
    row_count: int
    column_count: int
    columns: list[SurveyColumnMetadata]
    statistics: dict[str, Any]
    charts: list[dict[str, Any]] = Field(default_factory=list)
    quality_issues: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    survey: Optional[SurveyUploadResponse] = None


class SurveyListItem(BaseModel):
    id: int
    dataset_id: int
    title: str
    department: Optional[str] = None
    period: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SurveyDetailResponse(BaseModel):
    id: int
    dataset_id: int
    title: str
    department: Optional[str] = None
    period: Optional[str] = None
    quarter: Optional[str] = None
    year: Optional[int] = None
    source_sheet: str
    header_row: int
    data_start_row: int
    row_count: int
    column_count: int
    columns: list[SurveyColumnMetadata]
    questions: list[SurveyQuestionItem]
    report: Optional[SurveyReportItem] = None
    created_at: Optional[datetime] = None
