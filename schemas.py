from datetime import datetime
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ValueError("Geçerli bir e-posta adresi girin")
        return email


class UserCreate(UserCredentials):
    full_name: str = Field(min_length=3, max_length=160)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        full_name = " ".join(value.split())
        if len(full_name) < 3:
            raise ValueError("Ad soyad en az 3 karakter olmalidir")
        return full_name


class UserLogin(UserCredentials):
    pass


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    must_change_password: bool = False

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(extra="forbid")


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class DepartmentItem(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentCreateResponse(DepartmentItem):
    created: bool


class DepartmentListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[DepartmentItem] = Field(default_factory=list)


class AdminAnalystItem(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    created_at: Optional[datetime] = None


class AdminAnalystListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[AdminAnalystItem] = Field(default_factory=list)


class AdminAnalystDetail(AdminAnalystItem):
    department_count: int = 0
    dataset_count: int = 0
    analysis_count: int = 0
    report_count: int = 0


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
    ai_report: Optional[str] = None
    ai_report_status: str = "completed"
    ai_report_warning: Optional[str] = None
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
    dataset_id: Optional[int] = None
    analysis_type: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
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
    display_label: str
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
    ai_report: str = ""
    ai_report_status: str = "not_requested"
    ai_report_warning: Optional[str] = None
    created_at: Optional[datetime] = None


class SurveyQuestionScore(BaseModel):
    question_id: int
    question_no: Optional[str] = None
    label: str
    question_text: str
    score_100: Optional[float] = None
    response_count: int
    missing_count: int
    missing_pct: float
    distribution: list[dict[str, Any]] = Field(default_factory=list)


class SurveyGroupScore(BaseModel):
    label: str
    score_100: Optional[float] = None
    respondent_count: int
    low_sample: bool = False


class SurveyChartItem(BaseModel):
    id: str
    type: str
    title: str
    unit: str
    data: list[dict[str, Any]] = Field(default_factory=list)


class SurveyResearchResponse(BaseModel):
    survey_id: int
    report_id: int
    title: str
    status: str
    response_count: int
    scored_response_count: int
    likert_question_count: int
    overall_score_100: Optional[float] = None
    question_scores: list[SurveyQuestionScore] = Field(default_factory=list)
    gender_scores: list[SurveyGroupScore] = Field(default_factory=list)
    age_scores: list[SurveyGroupScore] = Field(default_factory=list)
    neighborhood_scores: list[SurveyGroupScore] = Field(default_factory=list)
    charts: list[SurveyChartItem] = Field(default_factory=list)
    quality_issues: list[dict[str, Any]] = Field(default_factory=list)
    ai_report: Optional[str] = None
    ai_report_status: str = "not_requested"
    ai_report_warning: Optional[str] = None
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
    department_id: int
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


class DatasetListItem(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_type: str
    detected_format: str
    row_count: int
    column_count: int
    department_id: int
    department_name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DatasetDetailResponse(DatasetListItem):
    columns: list[SurveyColumnMetadata]
    preview_rows: list[dict[str, Any]] = Field(default_factory=list)
    survey_id: Optional[int] = None
    latest_analysis_id: Optional[int] = None
    has_source_file: bool = False


class DatasetListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[DatasetListItem] = Field(default_factory=list)


class DatasetRowsResponse(BaseModel):
    dataset_id: int
    offset: int
    limit: int
    total: int
    rows: list[dict[str, Any]] = Field(default_factory=list)


class DatasetAnalysisCreate(BaseModel):
    template: str = Field(default="general", min_length=1, max_length=80)
    question: Optional[str] = Field(default=None, max_length=2_000)


class DatasetComparisonCreate(BaseModel):
    dataset_ids: list[int] = Field(min_length=2, max_length=2)
    question: Optional[str] = Field(default=None, max_length=2_000)

    @field_validator("dataset_ids")
    @classmethod
    def dataset_ids_are_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Karsilastirma icin iki farkli dataset secin")
        return value


class DatasetQuestionCreate(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class SurveyDetectionResponse(BaseModel):
    dataset_id: int
    detected: bool
    status: str
    survey_id: Optional[int] = None
    message: Optional[str] = None


class ReportCreate(BaseModel):
    analysis_ids: list[int] = Field(min_length=1, max_length=5)
    department_id: int = Field(gt=0)
    title: Optional[str] = Field(default=None, max_length=160)
    question: Optional[str] = Field(default=None, max_length=2_000)

    @field_validator("analysis_ids")
    @classmethod
    def analysis_ids_are_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Aynı analiz bir rapora birden fazla eklenemez")
        return value


class ReportListItem(BaseModel):
    id: int
    title: str
    status: str
    analysis_ids: list[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None


class ReportDetailResponse(ReportListItem):
    content: Optional[str] = None
    error_message: Optional[str] = None
    model_name: Optional[str] = None


class AnalysisListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[DataAnalysisListItem] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[ReportListItem] = Field(default_factory=list)


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


class SurveyListResponse(BaseModel):
    offset: int
    limit: int
    total: int
    items: list[SurveyListItem] = Field(default_factory=list)


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
