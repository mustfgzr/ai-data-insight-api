from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from schemas import (
    AdminAnalystDetail,
    AdminAnalystItem,
    AdminAnalystListResponse,
    DepartmentItem,
    DepartmentListResponse,
    SurveyListItem,
    SurveyListResponse,
)


def list_analysts(db: Session, offset: int, limit: int, query_text: str | None = None) -> AdminAnalystListResponse:
    query = db.query(models.User).filter(models.User.role == "analyst")
    if query_text and query_text.strip():
        term = f"%{query_text.strip().lower()}%"
        query = query.filter(
            func.lower(models.User.email).like(term) | func.lower(models.User.full_name).like(term)
        )
    total = query.count()
    users = query.order_by(models.User.full_name.asc(), models.User.email.asc()).offset(offset).limit(limit).all()
    return AdminAnalystListResponse(
        offset=offset,
        limit=limit,
        total=total,
        items=[_analyst_item(user) for user in users],
    )


def get_analyst_detail(db: Session, analyst_id: int) -> AdminAnalystDetail:
    analyst = _analyst_or_404(db, analyst_id)
    department_count = (
        db.query(models.Dataset.department_id)
        .filter(models.Dataset.user_id == analyst.id)
        .distinct()
        .count()
    )
    return AdminAnalystDetail(
        **_analyst_item(analyst).model_dump(),
        department_count=department_count,
        dataset_count=db.query(models.Dataset).filter(models.Dataset.user_id == analyst.id).count(),
        analysis_count=db.query(models.DataAnalysis).filter(models.DataAnalysis.user_id == analyst.id).count(),
        report_count=db.query(models.Report).filter(models.Report.user_id == analyst.id).count(),
    )


def list_analyst_departments(db: Session, analyst_id: int, offset: int, limit: int) -> DepartmentListResponse:
    _analyst_or_404(db, analyst_id)
    query = (
        db.query(models.Department)
        .join(models.Dataset, models.Dataset.department_id == models.Department.id)
        .filter(models.Dataset.user_id == analyst_id)
        .distinct()
    )
    total = query.count()
    departments = query.order_by(models.Department.name.asc()).offset(offset).limit(limit).all()
    return DepartmentListResponse(
        offset=offset,
        limit=limit,
        total=total,
        items=[DepartmentItem(id=item.id, name=item.name, created_at=item.created_at) for item in departments],
    )


def list_surveys(
    db: Session,
    user_id: int,
    offset: int,
    limit: int,
    department_id: int | None = None,
) -> SurveyListResponse:
    query = db.query(models.Survey).filter(models.Survey.user_id == user_id)
    if department_id is not None:
        query = query.join(models.Dataset, models.Dataset.id == models.Survey.dataset_id).filter(
            models.Dataset.department_id == department_id
        )
    total = query.count()
    surveys = query.order_by(models.Survey.created_at.desc(), models.Survey.id.desc()).offset(offset).limit(limit).all()
    return SurveyListResponse(
        offset=offset,
        limit=limit,
        total=total,
        items=[
            SurveyListItem(
                id=survey.id,
                dataset_id=survey.dataset_id,
                title=survey.title,
                department=survey.department,
                period=survey.period,
                quarter=survey.quarter,
                year=survey.year,
                created_at=survey.created_at,
            )
            for survey in surveys
        ],
    )


def _analyst_or_404(db: Session, analyst_id: int) -> models.User:
    analyst = db.query(models.User).filter(models.User.id == analyst_id, models.User.role == "analyst").first()
    if analyst is None:
        raise HTTPException(status_code=404, detail="Veri analisti bulunamadi")
    return analyst


def _analyst_item(analyst: models.User) -> AdminAnalystItem:
    return AdminAnalystItem(
        id=analyst.id,
        full_name=analyst.full_name,
        email=analyst.email,
    )
