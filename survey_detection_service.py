from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from dataset_analysis_service import get_dataset_source_or_409
from schemas import SurveyDetectionResponse
from survey_ingestor import parse_survey_content
from survey_storage import save_parsed_survey


def detect_survey_for_dataset(
    db: Session,
    user_id: int,
    dataset_id: int,
) -> SurveyDetectionResponse:
    dataset, source_file = get_dataset_source_or_409(db, user_id, dataset_id)
    existing = db.query(models.Survey).filter(models.Survey.dataset_id == dataset.id).first()
    if existing is not None:
        return SurveyDetectionResponse(
            dataset_id=dataset.id,
            detected=True,
            status="already_detected",
            survey_id=existing.id,
            message="Bu dataset icin survey kaydi zaten mevcut.",
        )

    try:
        parsed = parse_survey_content(dataset.original_filename, source_file.content)
    except HTTPException as exc:
        if exc.status_code == 422:
            return SurveyDetectionResponse(
                dataset_id=dataset.id,
                detected=False,
                status="not_survey",
                message="Dataset anket formati olarak algilanmadi.",
            )
        raise

    survey = save_parsed_survey(db, user_id, parsed, dataset=dataset)
    return SurveyDetectionResponse(
        dataset_id=dataset.id,
        detected=True,
        status="detected",
        survey_id=survey.survey_id,
        message="Dataset anket formati olarak algilandi.",
    )
