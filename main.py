import json
import os

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from database import engine
import models
from schemas import (
    UserCreate, UserResponse, Token, AnalysisResponse,
    DataAnalysisResponse, DataAnalysisListItem,
    CompareResponse, AskResponse,
    SurveyUploadResponse, SurveyListItem, SurveyDetailResponse,
)
from auth import hash_password, verify_password, create_access_token, get_db, get_current_user
from file_parser import extract_text
from ai_service import summarize_text
from data_ingestor import ingest_file
from stats_engine import analyze as stats_analyze, result_to_dict
from ai_analyst import strategic_analysis, compare_datasets, ask_about_data
from survey_ingestor import parse_survey_upload
from survey_storage import get_survey_detail, save_parsed_survey

if os.getenv("AUTO_CREATE_TABLES", "1") == "1":
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


@app.post("/analyze/compare", response_model=CompareResponse)
async def analyze_compare(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    question: str = Form(None),
    current_user: models.User = Depends(get_current_user),
):
    """İki veri setini karşılaştırır ve Gemini ile stratejik analiz üretir."""
    ingested1 = await ingest_file(file1)
    ingested2 = await ingest_file(file2)

    stats1 = stats_analyze(ingested1.df)
    stats2 = stats_analyze(ingested2.df)

    ai_report = compare_datasets(
        ingested1=ingested1, stats1=stats1,
        ingested2=ingested2, stats2=stats2,
        question=question,
    )

    return CompareResponse(
        file1=ingested1.filename,
        file2=ingested2.filename,
        ai_report=ai_report,
    )


@app.post("/analyze/ask", response_model=AskResponse)
async def analyze_ask(
    file: UploadFile = File(...),
    question: str = Form(...),
    current_user: models.User = Depends(get_current_user),
):
    """Veri seti hakkında doğal dilde soru sorar, Gemini yanıtlar."""
    ingested = await ingest_file(file)
    stats_result = stats_analyze(ingested.df)

    answer = ask_about_data(
        ingested=ingested,
        stats=stats_result,
        question=question,
    )

    return AskResponse(
        filename=ingested.filename,
        question=question,
        answer=answer,
    )


@app.get("/analyses", response_model=list[DataAnalysisListItem])
def list_analyses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının geçmiş veri analizlerini listeler."""
    records = (
        db.query(models.DataAnalysis)
        .filter(models.DataAnalysis.user_id == current_user.id)
        .order_by(models.DataAnalysis.created_at.desc())
        .all()
    )
    return records


@app.get("/analyses/{analysis_id}", response_model=DataAnalysisResponse)
def get_analysis(
    analysis_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Belirli bir veri analizinin detayını getirir."""
    record = (
        db.query(models.DataAnalysis)
        .filter(
            models.DataAnalysis.id == analysis_id,
            models.DataAnalysis.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı")

    return DataAnalysisResponse(
        id=record.id,
        filename=record.filename,
        template=record.template,
        row_count=record.row_count,
        column_count=record.column_count,
        columns_info=json.loads(record.columns_info) if record.columns_info else [],
        statistics=json.loads(record.statistics) if record.statistics else {},
        ai_report=record.ai_report or "",
        question=record.question,
        created_at=record.created_at,
    )


@app.post("/surveys/upload", response_model=SurveyUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_survey(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Anket CSV/Excel dosyasını okur, metadata/soru/cevap/rapor kayıtlarını oluşturur."""
    try:
        parsed = await parse_survey_upload(file)
        return save_parsed_survey(db, current_user.id, parsed)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Anket dosyası işlenirken hata oluştu: {exc}")


@app.get("/surveys", response_model=list[SurveyListItem])
def list_surveys(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının yüklediği anketleri listeler."""
    return (
        db.query(models.Survey)
        .filter(models.Survey.user_id == current_user.id)
        .order_by(models.Survey.created_at.desc())
        .all()
    )


@app.get("/surveys/{survey_id}", response_model=SurveyDetailResponse)
def get_survey(
    survey_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Anketin dataset, kolon, soru ve rapor özetini getirir."""
    detail = get_survey_detail(db, current_user.id, survey_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Anket bulunamadı")
    return detail
