from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

import models
from schemas import (
    AnalysisListResponse,
    DataAnalysisListItem,
    DataAnalysisResponse,
    DatasetDetailResponse,
    DatasetListItem,
    DatasetListResponse,
    DatasetRowsResponse,
    SurveyColumnMetadata,
)


def list_datasets(
    db: Session,
    user_id: int,
    offset: int,
    limit: int,
    department_id: int | None = None,
) -> DatasetListResponse:
    query = db.query(models.Dataset).filter(models.Dataset.user_id == user_id)
    if department_id is not None:
        query = query.filter(models.Dataset.department_id == department_id)
    total = query.count()
    datasets = (
        query.order_by(models.Dataset.created_at.desc(), models.Dataset.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return DatasetListResponse(
        offset=offset,
        limit=limit,
        total=total,
        items=[_dataset_list_item(dataset) for dataset in datasets],
    )


def get_dataset_detail(db: Session, user_id: int | None, dataset_id: int) -> DatasetDetailResponse | None:
    dataset = _owned_dataset(db, user_id, dataset_id)
    if dataset is None:
        return None

    columns = (
        db.query(models.DatasetColumn)
        .filter(models.DatasetColumn.dataset_id == dataset.id)
        .order_by(models.DatasetColumn.order_index)
        .all()
    )
    preview_rows = (
        db.query(models.DatasetRow)
        .filter(models.DatasetRow.dataset_id == dataset.id)
        .order_by(models.DatasetRow.row_index)
        .limit(5)
        .all()
    )
    survey = db.query(models.Survey).filter(models.Survey.dataset_id == dataset.id).first()
    analysis_query = db.query(models.DataAnalysis).filter(models.DataAnalysis.dataset_id == dataset.id)
    if user_id is not None:
        analysis_query = analysis_query.filter(models.DataAnalysis.user_id == user_id)
    analysis = analysis_query.order_by(models.DataAnalysis.id.desc()).first()
    source_file = db.query(models.DatasetFile.id).filter(models.DatasetFile.dataset_id == dataset.id).first()

    return DatasetDetailResponse(
        **_dataset_list_item(dataset).model_dump(),
        columns=[_column_schema(column) for column in columns],
        preview_rows=[_loads(row.data, {}) for row in preview_rows],
        survey_id=survey.id if survey else None,
        latest_analysis_id=analysis.id if analysis else None,
        has_source_file=source_file is not None,
    )


def get_dataset_rows(
    db: Session,
    user_id: int | None,
    dataset_id: int,
    offset: int,
    limit: int,
) -> DatasetRowsResponse | None:
    dataset = _owned_dataset(db, user_id, dataset_id)
    if dataset is None:
        return None

    query = db.query(models.DatasetRow).filter(models.DatasetRow.dataset_id == dataset.id)
    total = query.count()
    rows = query.order_by(models.DatasetRow.row_index).offset(offset).limit(limit).all()
    return DatasetRowsResponse(
        dataset_id=dataset.id,
        offset=offset,
        limit=limit,
        total=total,
        rows=[_loads(row.data, {}) for row in rows],
    )


def get_dataset_file(db: Session, user_id: int | None, dataset_id: int) -> models.DatasetFile | None:
    dataset = _owned_dataset(db, user_id, dataset_id)
    if dataset is None:
        return None
    return db.query(models.DatasetFile).filter(models.DatasetFile.dataset_id == dataset.id).first()


def list_analyses(
    db: Session,
    user_id: int,
    offset: int,
    limit: int,
    department_id: int | None = None,
) -> AnalysisListResponse:
    records = (
        db.query(models.DataAnalysis)
        .filter(models.DataAnalysis.user_id == user_id)
    )
    if department_id is not None:
        records = records.join(models.Dataset, models.DataAnalysis.dataset_id == models.Dataset.id).filter(
            models.Dataset.department_id == department_id
        )
    total = records.count()
    records = records.order_by(models.DataAnalysis.created_at.desc(), models.DataAnalysis.id.desc()).offset(offset).limit(limit).all()
    return AnalysisListResponse(offset=offset, limit=limit, total=total, items=[_analysis_list_item(record) for record in records])


def get_analysis_detail(db: Session, user_id: int | None, analysis_id: int) -> DataAnalysisResponse | None:
    query = db.query(models.DataAnalysis).filter(models.DataAnalysis.id == analysis_id)
    if user_id is not None:
        query = query.filter(models.DataAnalysis.user_id == user_id)
    record = query.first()
    if record is None:
        return None
    return _analysis_response(record)


def _owned_dataset(db: Session, user_id: int | None, dataset_id: int) -> models.Dataset | None:
    query = db.query(models.Dataset).filter(models.Dataset.id == dataset_id)
    if user_id is not None:
        query = query.filter(models.Dataset.user_id == user_id)
    return query.first()


def _dataset_list_item(dataset: models.Dataset) -> DatasetListItem:
    return DatasetListItem(
        id=dataset.id,
        filename=dataset.filename,
        original_filename=dataset.original_filename,
        file_type=dataset.file_type,
        detected_format=dataset.detected_format,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        department_id=dataset.department_id,
        department_name=None,
        created_at=dataset.created_at,
    )


def _column_schema(column: models.DatasetColumn) -> SurveyColumnMetadata:
    return SurveyColumnMetadata(
        name=column.name,
        dtype=column.dtype,
        semantic_type=column.semantic_type,
        missing_count=column.missing_count,
        missing_pct=column.missing_pct,
        unique_count=column.unique_count,
        sample_values=_loads(column.sample_values, []),
        code_map=_loads(column.code_map, {}),
    )


def _analysis_list_item(record: models.DataAnalysis) -> DataAnalysisListItem:
    return DataAnalysisListItem(
        id=record.id,
        filename=record.filename,
        template=record.template or "general",
        row_count=record.row_count or 0,
        column_count=record.column_count or 0,
        dataset_id=record.dataset_id,
        analysis_type=record.analysis_type,
        status=record.status,
        summary=record.summary,
        question=record.question,
        created_at=record.created_at,
    )


def _analysis_response(record: models.DataAnalysis) -> DataAnalysisResponse:
    return DataAnalysisResponse(
        id=record.id,
        filename=record.filename,
        template=record.template or "general",
        row_count=record.row_count or 0,
        column_count=record.column_count or 0,
        columns_info=_loads(record.columns_info, []),
        statistics=_loads(record.statistics, {}),
        ai_report=record.ai_report,
        ai_report_status=record.ai_report_status or "completed",
        ai_report_warning=record.ai_report_warning,
        dataset_id=record.dataset_id,
        analysis_type=record.analysis_type or "general",
        status=record.status or "completed",
        chart_data=_loads(record.chart_data, []),
        quality_issues=_loads(record.quality_issues, []),
        summary=record.summary or "",
        question=record.question,
        created_at=record.created_at,
    )


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
