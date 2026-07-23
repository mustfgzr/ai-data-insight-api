from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

import models
from analysis_utils import build_chart_data, build_data_quality_issues, build_data_summary
from data_ingestor import IngestedData, dataframe_records, ingest_content
from department_service import get_department_or_404
from schemas import DatasetUploadResponse, SurveyColumnMetadata
from stats_engine import analyze as stats_analyze, result_to_dict
from survey_ingestor import parse_survey_upload
from survey_storage import save_parsed_survey


async def upload_dataset(
    db: Session,
    user_id: int,
    department_id: int,
    file: UploadFile,
) -> DatasetUploadResponse:
    """Bir dosyayı survey veya genel dataset olarak kalıcılaştırır."""
    get_department_or_404(db, department_id)
    content = await file.read()

    try:
        parsed_survey = await parse_survey_upload(file, content=content)
    except HTTPException as exc:
        if exc.status_code == 413:
            raise
        parsed_survey = None

    if parsed_survey is not None:
        survey = save_parsed_survey(
            db,
            user_id,
            parsed_survey,
            source_content=content,
            content_type=file.content_type,
            department_id=department_id,
        )
        analysis = (
            db.query(models.DataAnalysis)
            .filter(
                models.DataAnalysis.dataset_id == survey.dataset_id,
                models.DataAnalysis.user_id == user_id,
            )
            .order_by(models.DataAnalysis.id.desc())
            .first()
        )
        if analysis is None:
            raise RuntimeError("Survey analizi kaydedilemedi")

        return DatasetUploadResponse(
            dataset_id=survey.dataset_id,
            analysis_id=analysis.id,
            department_id=department_id,
            survey_id=survey.survey_id,
            filename=survey.filename,
            detected_format="survey",
            row_count=survey.row_count,
            column_count=survey.column_count,
            columns=survey.columns,
            statistics=_loads(analysis.statistics, {}),
            charts=_loads(analysis.chart_data, []),
            quality_issues=_loads(analysis.quality_issues, []),
            summary=analysis.summary or "",
            survey=survey,
        )

    ingested = ingest_content(file.filename or "unknown", content)
    return _save_general_dataset(
        db=db,
        user_id=user_id,
        department_id=department_id,
        ingested=ingested,
        content=content,
        content_type=file.content_type,
    )


def _save_general_dataset(
    db: Session,
    user_id: int,
    department_id: int,
    ingested: IngestedData,
    content: bytes,
    content_type: str | None,
) -> DatasetUploadResponse:
    dataset = models.Dataset(
        user_id=user_id,
        department_id=department_id,
        filename=ingested.filename,
        original_filename=ingested.filename,
        file_type=_file_type(ingested.filename),
        detected_format="general",
        row_count=ingested.row_count,
        column_count=ingested.column_count,
    )
    db.add(dataset)
    db.flush()

    db.add(
        models.DatasetFile(
            dataset_id=dataset.id,
            content_type=content_type,
            size_bytes=len(content),
            checksum=hashlib.sha256(content).hexdigest(),
            content=content,
        )
    )

    for index, column in enumerate(ingested.columns):
        db.add(
            models.DatasetColumn(
                dataset_id=dataset.id,
                name=column.name,
                original_name=column.name,
                dtype=column.dtype,
                semantic_type=column.semantic_type,
                missing_count=column.missing_count,
                missing_pct=column.missing_pct,
                unique_count=column.unique_count,
                sample_values=_dumps(column.sample_values),
                code_map=_dumps({}),
                order_index=index,
            )
        )

    rows = dataframe_records(ingested.df)
    for index, row in enumerate(rows, start=1):
        db.add(
            models.DatasetRow(
                dataset_id=dataset.id,
                row_index=index,
                data=_dumps(row),
            )
        )

    statistics = result_to_dict(stats_analyze(ingested.df))
    quality_issues = build_data_quality_issues(ingested.df, ingested.columns)
    charts = build_chart_data(statistics)
    summary = build_data_summary(
        ingested.row_count,
        ingested.column_count,
        quality_issues,
    )
    analysis = models.DataAnalysis(
        user_id=user_id,
        dataset_id=dataset.id,
        filename=ingested.filename,
        template="general",
        analysis_type="general",
        status="completed",
        row_count=ingested.row_count,
        column_count=ingested.column_count,
        columns_info=_dumps(
            [
                {
                    "name": column.name,
                    "dtype": column.dtype,
                    "semantic_type": column.semantic_type,
                    "missing_count": column.missing_count,
                    "missing_pct": column.missing_pct,
                    "unique_count": column.unique_count,
                    "sample_values": column.sample_values,
                    "code_map": {},
                }
                for column in ingested.columns
            ]
        ),
        statistics=_dumps(statistics),
        chart_data=_dumps(charts),
        quality_issues=_dumps(quality_issues),
        summary=summary,
        ai_report="",
    )
    db.add(analysis)
    db.commit()
    db.refresh(dataset)
    db.refresh(analysis)

    return DatasetUploadResponse(
        dataset_id=dataset.id,
        analysis_id=analysis.id,
        department_id=dataset.department_id,
        filename=dataset.filename,
        detected_format="general",
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        columns=[
            SurveyColumnMetadata(
                name=column.name,
                dtype=column.dtype,
                semantic_type=column.semantic_type,
                missing_count=column.missing_count,
                missing_pct=column.missing_pct,
                unique_count=column.unique_count,
                sample_values=column.sample_values,
                code_map={},
            )
            for column in ingested.columns
        ],
        statistics=statistics,
        charts=charts,
        quality_issues=quality_issues,
        summary=summary,
    )


def _file_type(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)
