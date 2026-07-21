import json
import os
from urllib.parse import quote

from fastapi import FastAPI, Depends, HTTPException, Response, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import engine
import models
from schemas import (
    UserCreate, UserLogin, UserResponse, Token, AnalysisResponse,
    DataAnalysisResponse, DataAnalysisListItem,
    CompareResponse, AskResponse,
    DatasetAnalysisCreate, DatasetComparisonCreate, DatasetDetailResponse,
    DatasetListResponse, DatasetQuestionCreate, DatasetRowsResponse, DatasetUploadResponse,
    ReportCreate, ReportDetailResponse, ReportListItem,
    SurveyDetectionResponse, SurveyResearchResponse, SurveyUploadResponse, SurveyListItem, SurveyDetailResponse,
)
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from file_parser import extract_text
from ai_service import summarize_text
from data_ingestor import ingest_file
from stats_engine import analyze as stats_analyze, result_to_dict
from ai_analyst import (
    GEMINI_NOT_CONFIGURED_WARNING,
    ask_about_data,
    compare_datasets,
    is_gemini_configured,
    strategic_analysis,
)
from survey_ingestor import parse_survey_upload
from survey_storage import get_survey_detail, save_parsed_survey
from dataset_service import upload_dataset as process_dataset_upload
from dataset_analysis_service import (
    ask_about_owned_dataset,
    compare_owned_datasets,
    create_analysis_for_dataset,
)
from dataset_query_service import (
    get_analysis_detail,
    get_dataset_detail,
    get_dataset_file,
    get_dataset_rows,
    list_analyses as list_analysis_history,
    list_datasets as list_dataset_history,
)
from report_service import create_report as create_saved_report, get_report_detail, list_reports as list_saved_reports
from survey_detection_service import detect_survey_for_dataset
from survey_research_service import (
    create_survey_research_ai_summary,
    get_survey_research,
    refresh_survey_research,
)

if os.getenv("AUTO_CREATE_TABLES", "0") == "1":
    models.Base.metadata.create_all(bind=engine)

app = FastAPI()

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kayıtlı",
        )
    db.refresh(db_user)
    return db_user


@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı",
        )
    access_token = create_access_token(data={"sub": str(db_user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/users/me", response_model=UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


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

@app.post("/analyze/data", response_model=DataAnalysisResponse, deprecated=True)
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

    # 4. Gemini stratejik analiz temel veri analizinden bagimsizdir.
    ai_report = None
    ai_report_status = "skipped"
    ai_report_warning = GEMINI_NOT_CONFIGURED_WARNING
    if is_gemini_configured():
        try:
            ai_report = strategic_analysis(
                ingested=ingested,
                stats=stats_result,
                template_name=template,
                question=question,
            )
            ai_report_status = "completed"
            ai_report_warning = None
        except Exception:
            ai_report_status = "failed"
            ai_report_warning = "Gemini servisi kullanilamadigi icin AI raporu olusturulamadi."

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
        ai_report_status=ai_report_status,
        ai_report_warning=ai_report_warning,
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
        ai_report_status=db_record.ai_report_status,
        ai_report_warning=db_record.ai_report_warning,
        question=db_record.question,
        created_at=db_record.created_at,
    )


@app.post("/analyze/compare", response_model=CompareResponse, deprecated=True)
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


@app.post("/analyze/ask", response_model=AskResponse, deprecated=True)
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
    return list_analysis_history(db, current_user.id)


@app.get("/analyses/{analysis_id}", response_model=DataAnalysisResponse)
def get_analysis(
    analysis_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Belirli bir veri analizinin detayını getirir."""
    detail = get_analysis_detail(db, current_user.id, analysis_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı")
    return detail


@app.post(
    "/surveys/upload",
    response_model=SurveyUploadResponse,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def upload_survey(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Anket CSV/Excel dosyasını okur, metadata/soru/cevap/rapor kayıtlarını oluşturur."""
    try:
        content = await file.read()
        parsed = await parse_survey_upload(file, content=content)
        return save_parsed_survey(
            db,
            current_user.id,
            parsed,
            source_content=content,
            content_type=file.content_type,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Anket dosyası işlenirken hata oluştu: {exc}")


@app.post("/datasets/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """CSV/XLSX dosyasını survey veya genel dataset olarak işler ve kaydeder."""
    try:
        return await process_dataset_upload(db, current_user.id, file)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Dataset dosyası işlenirken hata oluştu: {exc}")


@app.post(
    "/datasets/{dataset_id}/analyses",
    response_model=DataAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_existing_dataset(
    dataset_id: int,
    request: DatasetAnalysisCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kalici dataset satirlarindan yeni ve bagimsiz bir analiz olusturur."""
    try:
        return create_analysis_for_dataset(
            db,
            current_user.id,
            dataset_id,
            request.template,
            request.question,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Dataset analizi olusturulamadi") from exc


@app.post("/datasets/{dataset_id}/detect-survey", response_model=SurveyDetectionResponse)
def detect_dataset_survey(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kalici kaynak dosyadan survey yapisini algilar ve varsa dataset'e baglar."""
    try:
        return detect_survey_for_dataset(db, current_user.id, dataset_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Survey algilama tamamlanamadi") from exc


@app.post("/datasets/{dataset_id}/ask", response_model=AskResponse)
def ask_about_existing_dataset(
    dataset_id: int,
    request: DatasetQuestionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ask_about_owned_dataset(db, current_user.id, dataset_id, request.question)


@app.post("/dataset-comparisons", response_model=CompareResponse)
def compare_existing_datasets(
    request: DatasetComparisonCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return compare_owned_datasets(db, current_user.id, request.dataset_ids, request.question)


@app.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_dataset_history(db, current_user.id, offset, limit)


@app.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = get_dataset_detail(db, current_user.id, dataset_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Dataset bulunamadı")
    return detail


@app.get("/datasets/{dataset_id}/rows", response_model=DatasetRowsResponse)
def get_dataset_row_page(
    dataset_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    page = get_dataset_rows(db, current_user.id, dataset_id, offset, limit)
    if page is None:
        raise HTTPException(status_code=404, detail="Dataset bulunamadı")
    return page


@app.get("/datasets/{dataset_id}/download")
def download_dataset_source(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = get_dataset_detail(db, current_user.id, dataset_id)
    source_file = get_dataset_file(db, current_user.id, dataset_id)
    if detail is None or source_file is None:
        raise HTTPException(status_code=404, detail="Kaynak dosya bulunamadı")

    filename = quote(detail.original_filename)
    return Response(
        content=source_file.content,
        media_type=source_file.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@app.post("/reports", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    request: ReportCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return create_saved_report(db, current_user.id, request)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Rapor kaydedilirken hata oluştu") from exc


@app.get("/reports", response_model=list[ReportListItem])
def list_reports(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_saved_reports(db, current_user.id)


@app.get("/reports/{report_id}", response_model=ReportDetailResponse)
def get_report(
    report_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = get_report_detail(db, current_user.id, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")
    return report


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


@app.get("/surveys/{survey_id}/research", response_model=SurveyResearchResponse)
def get_research_analysis(
    survey_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Anketin kaydedilmiş, Gemini'den bağımsız sayısal araştırma analizini getirir."""
    return get_survey_research(db, current_user.id, survey_id)


@app.post("/surveys/{survey_id}/research/refresh", response_model=SurveyResearchResponse)
def refresh_research_analysis(
    survey_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mevcut anket cevaplarından araştırma analizini dosya yüklemeden yeniden hesaplar."""
    try:
        return refresh_survey_research(db, current_user.id, survey_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Anket araştırma analizi oluşturulamadı") from exc


@app.post("/surveys/{survey_id}/research/ai-summary", response_model=SurveyResearchResponse)
def create_research_ai_summary(
    survey_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kaydedilmiş sayısal araştırma sonucundan isteğe bağlı Gemini özeti üretir."""
    try:
        return create_survey_research_ai_summary(db, current_user.id, survey_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Anket AI özeti oluşturulamadı") from exc
