import json

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from database import engine
import models
from schemas import (
    UserCreate, UserResponse, Token, AnalysisResponse,
    DataAnalysisResponse, DataAnalysisListItem,
    CompareResponse, AskResponse,
)
from auth import hash_password, verify_password, create_access_token, get_db, get_current_user
from file_parser import extract_text
from ai_service import summarize_text
from data_ingestor import ingest_file
from stats_engine import analyze as stats_analyze, result_to_dict
from ai_analyst import strategic_analysis

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def root():
    return {"mesaj": "API çalışıyor"}


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Aynı e-posta ile kayıt kontrolü
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kayıtlı",
        )
    db_user = models.User(
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı",
        )
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Dosyadan metin çıkar
    text = await extract_text(file)

    # 2. Gemini ile özetle
    summary = summarize_text(text)

    # 3. Veritabanına kaydet
    analysis = models.Analysis(
        user_id=current_user.id,
        filename=file.filename,
        summary=summary,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


# ── FAZ 3: Veri Analiz Motoru Endpoint'leri ───────────────────

@app.post("/analyze/data", response_model=DataAnalysisResponse)
async def analyze_data(
    file: UploadFile = File(...),
    template: str = Form("general"),
    question: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Veri dosyasını analiz eder: istatistik çıkar + Gemini stratejik rapor."""
    # 1. Veriyi ayrıştır
    ingested = await ingest_file(file)

    # 2. İstatistiksel analiz
    stats_result = stats_analyze(ingested.df)
    stats_dict = result_to_dict(stats_result)

    # 3. Sütun bilgilerini JSON'a çevir
    from dataclasses import asdict
    columns_info_list = [asdict(c) for c in ingested.columns]

    # 4. Gemini stratejik analiz
    ai_report = strategic_analysis(
        ingested=ingested,
        stats=stats_result,
        template_name=template,
        question=question,
    )

    # 5. Veritabanına kaydet
    db_record = models.DataAnalysis(
        user_id=current_user.id,
        filename=ingested.filename,
        template=template,
        row_count=ingested.row_count,
        column_count=ingested.column_count,
        columns_info=json.dumps(columns_info_list, ensure_ascii=False),
        statistics=json.dumps(stats_dict, ensure_ascii=False),
        ai_report=ai_report,
        question=question,
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # 6. JSON alanlarını parse ederek döndür
    return DataAnalysisResponse(
        id=db_record.id,
        filename=db_record.filename,
        template=db_record.template,
        row_count=db_record.row_count,
        column_count=db_record.column_count,
        columns_info=columns_info_list,
        statistics=stats_dict,
        ai_report=db_record.ai_report,
        question=db_record.question,
        created_at=db_record.created_at,
    )
