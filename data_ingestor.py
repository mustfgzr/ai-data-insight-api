"""
Akıllı Veri Ayrıştırıcı
========================
Excel (xlsx/xls) ve CSV dosyalarını pandas DataFrame'e dönüştürür.
Otomatik başlık algılama, veri tipi tespiti ve eksik veri raporu üretir.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import pandas as pd
from fastapi import HTTPException, UploadFile


SUPPORTED_DATA_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@dataclass
class ColumnInfo:
    """Tek bir sütun hakkında metadata."""
    name: str
    dtype: str          # "numeric", "categorical", "datetime", "boolean"
    missing_count: int
    missing_pct: float
    unique_count: int


@dataclass
class IngestedData:
    """Ayrıştırılmış veri seti ve metadata."""
    df: pd.DataFrame
    filename: str
    row_count: int
    column_count: int
    columns: list[ColumnInfo] = field(default_factory=list)
    preview_head: list[dict] = field(default_factory=list)  # İlk 5 satır
    preview_tail: list[dict] = field(default_factory=list)  # Son 5 satır


def _classify_dtype(series: pd.Series) -> str:
    """Pandas sütun tipini insan-okunur kategoriye dönüştürür."""
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Tarih olabilecek object sütunları dene
    if series.dtype == object:
        try:
            pd.to_datetime(series.dropna().head(20), infer_datetime_format=True)
            return "datetime"
        except (ValueError, TypeError):
            pass

    return "categorical"


def _build_columns_info(df: pd.DataFrame) -> list[ColumnInfo]:
    """Her sütun için metadata üretir."""
    infos = []
    for col in df.columns:
        series = df[col]
        missing = int(series.isna().sum())
        total = len(series)
        infos.append(ColumnInfo(
            name=str(col),
            dtype=_classify_dtype(series),
            missing_count=missing,
            missing_pct=round((missing / total) * 100, 1) if total > 0 else 0.0,
            unique_count=int(series.nunique()),
        ))
    return infos


def _read_csv(content: bytes) -> pd.DataFrame:
    """CSV dosyasını okur; ayraç ve encoding otomatik algılanır."""
    # Yaygın encoding'leri dene
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1254"):  # cp1254 = Türkçe Windows
        try:
            text = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text = content.decode("utf-8", errors="replace")

    # Ayraç algılama: ilk satıra bak
    first_line = text.split("\n")[0] if text else ""
    if "\t" in first_line:
        sep = "\t"
    elif ";" in first_line:
        sep = ";"
    else:
        sep = ","

    return pd.read_csv(io.StringIO(text), sep=sep)


def _read_excel(content: bytes, sheet_name: str | None = None) -> pd.DataFrame:
    """Excel dosyasını okur. sheet_name verilmezse ilk sayfayı alır."""
    xls = pd.ExcelFile(io.BytesIO(content))

    if sheet_name:
        if sheet_name not in xls.sheet_names:
            raise HTTPException(
                status_code=400,
                detail=f"'{sheet_name}' sayfası bulunamadı. "
                       f"Mevcut sayfalar: {', '.join(xls.sheet_names)}",
            )
        return pd.read_excel(xls, sheet_name=sheet_name)

    # Birden fazla sayfa varsa hepsini birleştir (üst üste)
    if len(xls.sheet_names) == 1:
        return pd.read_excel(xls, sheet_name=xls.sheet_names[0])

    frames = []
    for name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=name)
        df["_sheet_name"] = name  # Hangi sayfadan geldiğini işaretle
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


async def ingest_file(
    file: UploadFile,
    sheet_name: str | None = None,
) -> IngestedData:
    """
    Yüklenen dosyayı ayrıştırır ve IngestedData döndürür.

    Desteklenen formatlar: .xlsx, .xls, .csv
    """
    filename = file.filename or "unknown"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in SUPPORTED_DATA_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen format: '{ext}'. "
                   f"Desteklenen: {', '.join(sorted(SUPPORTED_DATA_EXTENSIONS))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Dosya boş")

    # Formatına göre oku
    if ext == ".csv":
        df = _read_csv(content)
    else:
        df = _read_excel(content, sheet_name)

    # Tamamen boş satır/sütunları temizle
    df = df.dropna(how="all").dropna(axis=1, how="all")

    if df.empty:
        raise HTTPException(status_code=400, detail="Dosyada işlenebilir veri bulunamadı")

    # Sayısal olabilecek sütunları dönüştürmeyi dene
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors="raise")
            except (ValueError, TypeError):
                pass

    # Metadata oluştur
    columns_info = _build_columns_info(df)

    # Önizleme (NaN → None)
    head = df.head(5).where(df.head(5).notna(), None).to_dict(orient="records")
    tail = df.tail(5).where(df.tail(5).notna(), None).to_dict(orient="records")

    return IngestedData(
        df=df,
        filename=filename,
        row_count=len(df),
        column_count=len(df.columns),
        columns=columns_info,
        preview_head=head,
        preview_tail=tail,
    )
