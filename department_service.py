from __future__ import annotations

import re
import unicodedata

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from schemas import DepartmentCreateResponse, DepartmentItem, DepartmentListResponse


UNASSIGNED_DEPARTMENT_NAME = "Atanmamis"


def normalize_department_name(value: str) -> tuple[str, str]:
    name = " ".join(value.strip().split())
    if len(name) < 2:
        raise HTTPException(status_code=422, detail="Mudurluk adi en az 2 karakter olmalidir")
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    name_key = re.sub(r"\s+", " ", ascii_name).casefold().strip()
    return name, name_key


def list_departments(db: Session, offset: int, limit: int, query_text: str | None = None) -> DepartmentListResponse:
    query = db.query(models.Department)
    if query_text and query_text.strip():
        raw_query = " ".join(query_text.strip().split())
        normalized = unicodedata.normalize("NFKD", raw_query)
        key = re.sub(r"\s+", " ", "".join(char for char in normalized if not unicodedata.combining(char))).casefold().strip()
        query = query.filter(models.Department.name_key.contains(key))
    total = query.count()
    departments = query.order_by(models.Department.name.asc()).offset(offset).limit(limit).all()
    return DepartmentListResponse(
        offset=offset,
        limit=limit,
        total=total,
        items=[_item(department) for department in departments],
    )


def create_department(db: Session, name: str) -> DepartmentCreateResponse:
    display_name, name_key = normalize_department_name(name)
    existing = db.query(models.Department).filter(models.Department.name_key == name_key).first()
    if existing is not None:
        return DepartmentCreateResponse(**_item(existing).model_dump(), created=False)

    department = models.Department(name=display_name, name_key=name_key)
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        department = db.query(models.Department).filter(models.Department.name_key == name_key).first()
        if department is None:
            raise
        return DepartmentCreateResponse(**_item(department).model_dump(), created=False)
    db.refresh(department)
    return DepartmentCreateResponse(**_item(department).model_dump(), created=True)


def get_department_or_404(db: Session, department_id: int) -> models.Department:
    department = db.query(models.Department).filter(models.Department.id == department_id).first()
    if department is None:
        raise HTTPException(status_code=404, detail="Mudurluk bulunamadi")
    return department


def _item(department: models.Department) -> DepartmentItem:
    return DepartmentItem(id=department.id, name=department.name, created_at=department.created_at)
