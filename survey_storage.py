from __future__ import annotations

import json
import hashlib
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

import models
from analysis_utils import build_survey_chart_data
from schemas import (
    SurveyColumnMetadata,
    SurveyDetailResponse,
    SurveyQuestionItem,
    SurveyReportItem,
    SurveyUploadResponse,
)
from survey_ingestor import ParsedSurvey, question_display_label
from survey_research_service import build_and_save_survey_research


def save_parsed_survey(
    db: Session,
    user_id: int,
    parsed: ParsedSurvey,
    source_content: bytes | None = None,
    content_type: str | None = None,
    dataset: models.Dataset | None = None,
    department_id: int | None = None,
) -> SurveyUploadResponse:
    if dataset is None:
        if department_id is None:
            raise ValueError("Survey kaydi icin mudurluk zorunludur")
        dataset = models.Dataset(
            user_id=user_id,
            department_id=department_id,
            filename=parsed.filename,
            original_filename=parsed.filename,
            file_type=parsed.file_type,
            detected_format="survey",
            row_count=parsed.row_count,
            column_count=parsed.column_count,
        )
        db.add(dataset)
        db.flush()
    else:
        if dataset.user_id != user_id:
            raise ValueError("Survey dataset sahibiyle uyusmuyor")
        _replace_dataset_contents(db, dataset, parsed)

    if source_content is not None and dataset is not None:
        db.add(
            models.DatasetFile(
                dataset_id=dataset.id,
                content_type=content_type,
                size_bytes=len(source_content),
                checksum=hashlib.sha256(source_content).hexdigest(),
                content=source_content,
            )
        )

    dataset_columns: dict[str, models.DatasetColumn] = {}
    for column in parsed.columns:
        db_column = models.DatasetColumn(
            dataset_id=dataset.id,
            name=column.name,
            original_name=column.original_name,
            dtype=column.dtype,
            semantic_type=column.semantic_type,
            missing_count=column.missing_count,
            missing_pct=column.missing_pct,
            unique_count=column.unique_count,
            sample_values=_dumps(column.sample_values),
            code_map=_dumps(column.code_map),
            order_index=column.order_index,
        )
        db.add(db_column)
        db.flush()
        dataset_columns[column.name] = db_column

    dataset_rows: list[models.DatasetRow] = []
    for index, row in enumerate(parsed.rows, start=1):
        db_row = models.DatasetRow(
            dataset_id=dataset.id,
            row_index=index,
            data=_dumps(row),
        )
        db.add(db_row)
        db.flush()
        dataset_rows.append(db_row)

    survey = models.Survey(
        dataset_id=dataset.id,
        user_id=user_id,
        title=parsed.title,
        department=parsed.department,
        period=parsed.period,
        quarter=parsed.quarter,
        year=parsed.year,
        source_sheet=parsed.source_sheet,
        header_row=parsed.header_row,
        data_start_row=parsed.data_start_row,
    )
    db.add(survey)
    db.flush()

    question_models: dict[str, models.SurveyQuestion] = {}
    for question in parsed.questions:
        db_question = models.SurveyQuestion(
            survey_id=survey.id,
            dataset_column_id=dataset_columns[question.column_name].id,
            column_name=question.column_name,
            question_no=question.question_no,
            question_text=question.question_text,
            question_type=question.question_type,
            scale_type=question.scale_type,
            options=_dumps(question.options),
            is_likert=question.is_likert,
            is_demographic=question.is_demographic,
            is_open_text=question.is_open_text,
            order_index=question.order_index,
        )
        db.add(db_question)
        db.flush()
        question_models[question.column_name] = db_question

    for db_row, row in zip(dataset_rows, parsed.rows):
        response = models.SurveyResponse(
            survey_id=survey.id,
            dataset_row_id=db_row.id,
            respondent_no=_as_text(_find_no_value(row)),
            submitted_at=_find_submitted_at(row),
        )
        db.add(response)
        db.flush()

        for question in parsed.questions:
            raw_value = row.get(question.column_name)
            option_key = _option_key(raw_value)
            option_label = question.options.get(option_key)
            answer = models.SurveyAnswer(
                response_id=response.id,
                question_id=question_models[question.column_name].id,
                raw_value=_as_text(raw_value),
                normalized_value=option_label or _as_text(raw_value),
                numeric_value=_to_float(raw_value),
                option_label=option_label,
            )
            db.add(answer)

    report = build_and_save_survey_research(db, survey)

    db.add(
        models.DataAnalysis(
            user_id=user_id,
            dataset_id=dataset.id,
            filename=parsed.filename,
            template="survey",
            analysis_type="survey",
            status="completed",
            row_count=parsed.row_count,
            column_count=parsed.column_count,
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
                        "code_map": column.code_map,
                    }
                    for column in parsed.columns
                ]
            ),
            statistics=_dumps(
                {
                    "summary": parsed.report.summary,
                    "metrics": parsed.report.metrics,
                }
            ),
            chart_data=_dumps(build_survey_chart_data(parsed.report.metrics)),
            quality_issues=_dumps(parsed.report.quality_issues),
            summary=parsed.report.report_text,
            ai_report="",
        )
    )
    db.commit()
    db.refresh(dataset)
    db.refresh(survey)
    db.refresh(report)

    return _build_upload_response(dataset, survey, report, parsed)


def _replace_dataset_contents(
    db: Session,
    dataset: models.Dataset,
    parsed: ParsedSurvey,
) -> None:
    """Survey algilandiginda mevcut dataset'i kanonik survey satirlariyla gunceller."""
    db.query(models.DatasetRow).filter(models.DatasetRow.dataset_id == dataset.id).delete(
        synchronize_session=False
    )
    db.query(models.DatasetColumn).filter(models.DatasetColumn.dataset_id == dataset.id).delete(
        synchronize_session=False
    )
    dataset.filename = parsed.filename
    dataset.original_filename = parsed.filename
    dataset.file_type = parsed.file_type
    dataset.detected_format = "survey"
    dataset.row_count = parsed.row_count
    dataset.column_count = parsed.column_count
    db.flush()


def get_survey_detail(db: Session, user_id: int | None, survey_id: int) -> SurveyDetailResponse | None:
    query = db.query(models.Survey).filter(models.Survey.id == survey_id)
    if user_id is not None:
        query = query.filter(models.Survey.user_id == user_id)
    survey = query.first()
    if survey is None:
        return None

    dataset = db.query(models.Dataset).filter(models.Dataset.id == survey.dataset_id).first()
    columns = (
        db.query(models.DatasetColumn)
        .filter(models.DatasetColumn.dataset_id == survey.dataset_id)
        .order_by(models.DatasetColumn.order_index)
        .all()
    )
    questions = (
        db.query(models.SurveyQuestion)
        .filter(models.SurveyQuestion.survey_id == survey.id)
        .order_by(models.SurveyQuestion.order_index)
        .all()
    )
    report = (
        db.query(models.SurveyReport)
        .filter(models.SurveyReport.survey_id == survey.id)
        .order_by(models.SurveyReport.created_at.desc())
        .first()
    )

    return SurveyDetailResponse(
        id=survey.id,
        dataset_id=survey.dataset_id,
        title=survey.title,
        department=survey.department,
        period=survey.period,
        quarter=survey.quarter,
        year=survey.year,
        source_sheet=survey.source_sheet,
        header_row=survey.header_row,
        data_start_row=survey.data_start_row,
        row_count=dataset.row_count if dataset else 0,
        column_count=dataset.column_count if dataset else 0,
        columns=[_column_schema(column) for column in columns],
        questions=[_question_schema(question) for question in questions],
        report=_report_schema(report) if report else None,
        created_at=survey.created_at,
    )


def _build_upload_response(
    dataset: models.Dataset,
    survey: models.Survey,
    report: models.SurveyReport,
    parsed: ParsedSurvey,
) -> SurveyUploadResponse:
    return SurveyUploadResponse(
        dataset_id=dataset.id,
        survey_id=survey.id,
        filename=dataset.filename,
        title=survey.title,
        source_sheet=survey.source_sheet,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        header_row=survey.header_row,
        data_start_row=survey.data_start_row,
        columns=[
            SurveyColumnMetadata(
                name=column.name,
                dtype=column.dtype,
                semantic_type=column.semantic_type,
                missing_count=column.missing_count,
                missing_pct=column.missing_pct,
                unique_count=column.unique_count,
                sample_values=column.sample_values,
                code_map=column.code_map,
            )
            for column in parsed.columns
        ],
        questions=[
            SurveyQuestionItem(
                column_name=question.column_name,
                question_no=question.question_no,
                question_text=question.question_text,
                display_label=question.display_label,
                question_type=question.question_type,
                scale_type=question.scale_type,
                options=question.options,
                is_likert=question.is_likert,
                is_demographic=question.is_demographic,
                is_open_text=question.is_open_text,
            )
            for question in parsed.questions
        ],
        report=_report_schema(report),
        created_at=survey.created_at,
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


def _question_schema(question: models.SurveyQuestion) -> SurveyQuestionItem:
    return SurveyQuestionItem(
        id=question.id,
        column_name=question.column_name,
        question_no=question.question_no,
        question_text=question.question_text,
        display_label=question_display_label(question.question_text),
        question_type=question.question_type,
        scale_type=question.scale_type,
        options=_loads(question.options, {}),
        is_likert=bool(question.is_likert),
        is_demographic=bool(question.is_demographic),
        is_open_text=bool(question.is_open_text),
    )


def _report_schema(report: models.SurveyReport) -> SurveyReportItem:
    return SurveyReportItem(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        summary=_loads(report.summary, {}),
        metrics=_loads(report.metrics, {}),
        quality_issues=_loads(report.quality_issues, []),
        ai_report=report.ai_report or "",
        ai_report_status=report.ai_report_status,
        ai_report_warning=report.ai_report_warning,
        created_at=report.created_at,
    )


def _find_no_value(row: dict[str, Any]) -> Any:
    for key, value in row.items():
        if str(key).strip().lower().startswith("no"):
            return value
    return None


def _find_submitted_at(row: dict[str, Any]) -> datetime | None:
    for key, value in row.items():
        if "tarih" not in str(key).lower():
            continue
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
    return None


def _option_key(value: Any) -> str:
    number = _to_float(value)
    if number is not None and number.is_integer():
        return str(int(number))
    return "" if value is None else str(value).strip()


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
