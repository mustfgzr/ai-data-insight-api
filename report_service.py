from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from ai_analyst import MODEL, generate_report_from_analyses
from schemas import ReportCreate, ReportDetailResponse, ReportListItem


def create_report(db: Session, user_id: int, request: ReportCreate) -> ReportDetailResponse:
    analyses = _get_owned_analyses(db, user_id, request.analysis_ids)
    title = request.title.strip() if request.title and request.title.strip() else f"{len(analyses)} analiz için rapor"
    report = models.Report(
        user_id=user_id,
        title=title,
        status="processing",
        model_name=MODEL,
    )
    db.add(report)
    db.flush()

    for order_index, analysis in enumerate(analyses):
        db.add(
            models.ReportAnalysis(
                report_id=report.id,
                analysis_id=analysis.id,
                order_index=order_index,
            )
        )

    try:
        prompt, content = generate_report_from_analyses(analyses, request.question)
    except Exception as exc:
        report.status = "failed"
        report.error_message = "Gemini raporu oluşturulamadı"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Gemini raporu oluşturulamadı. Daha sonra tekrar deneyin.",
        ) from exc

    report.prompt = prompt
    report.content = content
    report.status = "completed"
    db.commit()
    db.refresh(report)
    return _report_detail(db, report)


def list_reports(db: Session, user_id: int) -> list[ReportListItem]:
    reports = (
        db.query(models.Report)
        .filter(models.Report.user_id == user_id)
        .order_by(models.Report.created_at.desc(), models.Report.id.desc())
        .all()
    )
    return [_report_list_item(db, report) for report in reports]


def get_report_detail(db: Session, user_id: int, report_id: int) -> ReportDetailResponse | None:
    report = (
        db.query(models.Report)
        .filter(models.Report.id == report_id, models.Report.user_id == user_id)
        .first()
    )
    if report is None:
        return None
    return _report_detail(db, report)


def _get_owned_analyses(
    db: Session,
    user_id: int,
    analysis_ids: list[int],
) -> list[models.DataAnalysis]:
    records = (
        db.query(models.DataAnalysis)
        .filter(
            models.DataAnalysis.user_id == user_id,
            models.DataAnalysis.id.in_(analysis_ids),
        )
        .all()
    )
    by_id = {record.id: record for record in records}
    missing_ids = [analysis_id for analysis_id in analysis_ids if analysis_id not in by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Seçilen analizlerden biri bulunamadı")
    return [by_id[analysis_id] for analysis_id in analysis_ids]


def _report_list_item(db: Session, report: models.Report) -> ReportListItem:
    links = (
        db.query(models.ReportAnalysis)
        .filter(models.ReportAnalysis.report_id == report.id)
        .order_by(models.ReportAnalysis.order_index)
        .all()
    )
    return ReportListItem(
        id=report.id,
        title=report.title,
        status=report.status,
        analysis_ids=[link.analysis_id for link in links],
        created_at=report.created_at,
    )


def _report_detail(db: Session, report: models.Report) -> ReportDetailResponse:
    return ReportDetailResponse(
        **_report_list_item(db, report).model_dump(),
        content=report.content,
        error_message=report.error_message,
        model_name=report.model_name,
    )
