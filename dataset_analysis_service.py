from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from ai_analyst import (
    GEMINI_NOT_CONFIGURED_WARNING,
    ask_about_data,
    compare_datasets,
    is_gemini_configured,
    strategic_analysis,
)
from analysis_utils import build_chart_data, build_data_quality_issues, build_data_summary
from data_ingestor import ColumnInfo, IngestedData, dataframe_records
from schemas import AskResponse, CompareResponse, DataAnalysisResponse
from stats_engine import analyze as stats_analyze, result_to_dict


def create_analysis_for_dataset(
    db: Session,
    user_id: int,
    dataset_id: int,
    template: str,
    question: str | None,
) -> DataAnalysisResponse:
    dataset, ingested = _load_dataset_ingested(db, user_id, dataset_id)
    stats_result = stats_analyze(ingested.df)
    statistics = result_to_dict(stats_result)
    quality_issues = build_data_quality_issues(ingested.df, ingested.columns)
    charts = build_chart_data(statistics)
    summary = build_data_summary(ingested.row_count, ingested.column_count, quality_issues)

    ai_report, ai_report_status, ai_report_warning = _create_ai_report(
        ingested,
        stats_result,
        template,
        question,
    )
    record = models.DataAnalysis(
        user_id=user_id,
        dataset_id=dataset.id,
        filename=dataset.filename,
        template=template,
        analysis_type="dataset",
        status="completed",
        row_count=ingested.row_count,
        column_count=ingested.column_count,
        columns_info=_dumps([asdict(column) for column in ingested.columns]),
        statistics=_dumps(statistics),
        chart_data=_dumps(charts),
        quality_issues=_dumps(quality_issues),
        summary=summary,
        ai_report=ai_report,
        ai_report_status=ai_report_status,
        ai_report_warning=ai_report_warning,
        question=question,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _analysis_response(record, statistics, charts, quality_issues, ingested.columns)


def compare_owned_datasets(
    db: Session,
    user_id: int,
    dataset_ids: list[int],
    question: str | None,
) -> CompareResponse:
    if len(dataset_ids) != 2 or len(set(dataset_ids)) != 2:
        raise HTTPException(status_code=422, detail="Karsilastirma icin iki farkli dataset secin")

    first_dataset, first = _load_dataset_ingested(db, user_id, dataset_ids[0])
    second_dataset, second = _load_dataset_ingested(db, user_id, dataset_ids[1])
    if not is_gemini_configured():
        return CompareResponse(
            file1=first_dataset.filename,
            file2=second_dataset.filename,
            ai_report=GEMINI_NOT_CONFIGURED_WARNING,
        )

    try:
        report = compare_datasets(
            ingested1=first,
            stats1=stats_analyze(first.df),
            ingested2=second,
            stats2=stats_analyze(second.df),
            question=question,
        )
    except Exception:
        report = "Gemini servisi kullanilamadigi icin karsilastirma raporu olusturulamadi."
    return CompareResponse(file1=first_dataset.filename, file2=second_dataset.filename, ai_report=report)


def ask_about_owned_dataset(
    db: Session,
    user_id: int,
    dataset_id: int,
    question: str,
) -> AskResponse:
    dataset, ingested = _load_dataset_ingested(db, user_id, dataset_id)
    if not is_gemini_configured():
        return AskResponse(
            filename=dataset.filename,
            question=question,
            answer=GEMINI_NOT_CONFIGURED_WARNING,
        )
    try:
        answer = ask_about_data(ingested=ingested, stats=stats_analyze(ingested.df), question=question)
    except Exception:
        answer = "Gemini servisi kullanilamadigi icin soru yanitlanamadi."
    return AskResponse(filename=dataset.filename, question=question, answer=answer)


def get_owned_dataset_or_404(db: Session, user_id: int, dataset_id: int) -> models.Dataset:
    dataset = (
        db.query(models.Dataset)
        .filter(models.Dataset.id == dataset_id, models.Dataset.user_id == user_id)
        .first()
    )
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset bulunamadi")
    return dataset


def get_dataset_source_or_409(
    db: Session,
    user_id: int,
    dataset_id: int,
) -> tuple[models.Dataset, models.DatasetFile]:
    dataset = get_owned_dataset_or_404(db, user_id, dataset_id)
    source_file = (
        db.query(models.DatasetFile)
        .filter(models.DatasetFile.dataset_id == dataset.id)
        .first()
    )
    if source_file is None or not source_file.content:
        raise HTTPException(status_code=409, detail="Dataset kaynak dosyasi kullanilamiyor")
    return dataset, source_file


def _load_dataset_ingested(
    db: Session,
    user_id: int,
    dataset_id: int,
) -> tuple[models.Dataset, IngestedData]:
    dataset = get_owned_dataset_or_404(db, user_id, dataset_id)
    row_models = (
        db.query(models.DatasetRow)
        .filter(models.DatasetRow.dataset_id == dataset.id)
        .order_by(models.DatasetRow.row_index)
        .all()
    )
    if not row_models:
        raise HTTPException(status_code=409, detail="Dataset analiz edilecek satir verisi icermiyor")

    column_models = (
        db.query(models.DatasetColumn)
        .filter(models.DatasetColumn.dataset_id == dataset.id)
        .order_by(models.DatasetColumn.order_index)
        .all()
    )
    rows = [_loads(row.data, {}) for row in row_models]
    frame = pd.DataFrame(rows)
    columns = [_column_info(column) for column in column_models]
    for column in columns:
        if column.name not in frame.columns:
            frame[column.name] = None
        if column.dtype == "numeric":
            frame[column.name] = pd.to_numeric(frame[column.name], errors="coerce")
        elif column.dtype == "datetime":
            frame[column.name] = pd.to_datetime(frame[column.name], errors="coerce")

    return dataset, IngestedData(
        df=frame,
        filename=dataset.filename,
        row_count=len(frame),
        column_count=len(frame.columns),
        columns=columns,
        preview_head=dataframe_records(frame.head(5)),
        preview_tail=dataframe_records(frame.tail(5)),
    )


def _create_ai_report(
    ingested: IngestedData,
    stats: Any,
    template: str,
    question: str | None,
) -> tuple[str | None, str, str | None]:
    if not is_gemini_configured():
        return None, "skipped", GEMINI_NOT_CONFIGURED_WARNING
    try:
        report = strategic_analysis(
            ingested=ingested,
            stats=stats,
            template_name=template,
            question=question,
        )
        return report, "completed", None
    except Exception:
        return None, "failed", "Gemini servisi kullanilamadigi icin AI raporu olusturulamadi."


def _analysis_response(
    record: models.DataAnalysis,
    statistics: dict[str, Any],
    charts: list[dict[str, Any]],
    quality_issues: list[dict[str, Any]],
    columns: list[ColumnInfo],
) -> DataAnalysisResponse:
    return DataAnalysisResponse(
        id=record.id,
        filename=record.filename,
        template=record.template or "general",
        row_count=record.row_count or 0,
        column_count=record.column_count or 0,
        columns_info=[asdict(column) for column in columns],
        statistics=statistics,
        ai_report=record.ai_report,
        ai_report_status=record.ai_report_status,
        ai_report_warning=record.ai_report_warning,
        dataset_id=record.dataset_id,
        analysis_type=record.analysis_type or "dataset",
        status=record.status or "completed",
        chart_data=charts,
        quality_issues=quality_issues,
        summary=record.summary or "",
        question=record.question,
        created_at=record.created_at,
    )


def _column_info(column: models.DatasetColumn) -> ColumnInfo:
    return ColumnInfo(
        name=column.name,
        dtype=column.dtype,
        semantic_type=column.semantic_type,
        missing_count=column.missing_count,
        missing_pct=column.missing_pct,
        unique_count=column.unique_count,
        sample_values=_loads(column.sample_values, []),
    )


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)
