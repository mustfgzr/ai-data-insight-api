from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class AnalysisResponse(BaseModel):
    id: int
    filename: str
    summary: str

    class Config:
        from_attributes = True


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
    question: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataAnalysisListItem(BaseModel):
    id: int
    filename: str
    template: str
    row_count: int
    column_count: int
    question: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompareResponse(BaseModel):
    file1: str
    file2: str
    ai_report: str


class AskResponse(BaseModel):
    filename: str
    question: str
    answer: str
