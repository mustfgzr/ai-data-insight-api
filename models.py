from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    summary = Column(Text)


class DataAnalysis(Base):
    __tablename__ = "data_analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    template = Column(String, default="general")
    analysis_type = Column(String, default="dataset")
    status = Column(String, default="completed")
    row_count = Column(Integer)
    column_count = Column(Integer)
    columns_info = Column(Text)       # JSON: sütun adları + tipler
    statistics = Column(Text)         # JSON: istatistik sonuçları
    chart_data = Column(Text)         # JSON: frontend grafik verileri
    quality_issues = Column(Text)     # JSON: veri kalite uyarıları
    summary = Column(Text)             # Kural tabanlı kısa özet
    ai_report = Column(Text)          # Gemini stratejik rapor
    question = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    detected_format = Column(String, default="survey")
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, unique=True, index=True)
    content_type = Column(String)
    size_bytes = Column(Integer, nullable=False)
    checksum = Column(String, nullable=False, index=True)
    content = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    original_name = Column(Text, nullable=False)
    dtype = Column(String, nullable=False)
    semantic_type = Column(String, default="unknown")
    missing_count = Column(Integer, default=0)
    missing_pct = Column(Float, default=0.0)
    unique_count = Column(Integer, default=0)
    sample_values = Column(Text)
    code_map = Column(Text)
    order_index = Column(Integer, default=0)


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    data = Column(Text, nullable=False)


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    department = Column(String)
    period = Column(String)
    quarter = Column(String)
    year = Column(Integer)
    source_sheet = Column(String, nullable=False)
    header_row = Column(Integer, nullable=False)
    data_start_row = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False, index=True)
    dataset_column_id = Column(Integer, ForeignKey("dataset_columns.id"), nullable=False)
    column_name = Column(String, nullable=False)
    question_no = Column(String)
    question_text = Column(Text, nullable=False)
    question_type = Column(String, default="unknown")
    scale_type = Column(String)
    options = Column(Text)
    is_likert = Column(Boolean, default=False)
    is_demographic = Column(Boolean, default=False)
    is_open_text = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False, index=True)
    dataset_row_id = Column(Integer, ForeignKey("dataset_rows.id"), nullable=False)
    respondent_no = Column(String)
    submitted_at = Column(DateTime)


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("survey_responses.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id"), nullable=False, index=True)
    raw_value = Column(Text)
    normalized_value = Column(Text)
    numeric_value = Column(Float)
    option_label = Column(Text)


class SurveyReport(Base):
    __tablename__ = "survey_reports"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False, index=True)
    report_type = Column(String, default="auto")
    status = Column(String, default="completed")
    summary = Column(Text)
    metrics = Column(Text)
    quality_issues = Column(Text)
    ai_report = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    prompt = Column(Text)
    content = Column(Text)
    error_message = Column(Text)
    model_name = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class ReportAnalysis(Base):
    __tablename__ = "report_analyses"
    __table_args__ = (
        UniqueConstraint("report_id", "analysis_id", name="uq_report_analyses_report_analysis"),
    )

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    analysis_id = Column(Integer, ForeignKey("data_analyses.id"), nullable=False, index=True)
    order_index = Column(Integer, default=0, nullable=False)
