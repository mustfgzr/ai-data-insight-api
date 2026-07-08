from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
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
    filename = Column(String, nullable=False)
    template = Column(String, default="general")
    row_count = Column(Integer)
    column_count = Column(Integer)
    columns_info = Column(Text)       # JSON: sütun adları + tipler
    statistics = Column(Text)         # JSON: istatistik sonuçları
    ai_report = Column(Text)          # Gemini stratejik rapor
    question = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
