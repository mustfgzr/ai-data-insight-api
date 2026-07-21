from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from ai_analyst import (
    GEMINI_NOT_CONFIGURED_WARNING,
    generate_survey_research_summary,
    is_gemini_configured,
)
from schemas import SurveyResearchResponse
from survey_ingestor import question_display_label


MIN_CHART_SAMPLE = 3
AGE_BANDS = (
    (0, 17, "18 yaş altı"),
    (18, 24, "18-24"),
    (25, 34, "25-34"),
    (35, 44, "35-44"),
    (45, 54, "45-54"),
    (55, 64, "55-64"),
    (65, 120, "65+"),
)


def get_survey_research(
    db: Session,
    user_id: int,
    survey_id: int,
) -> SurveyResearchResponse:
    survey = _get_owned_survey(db, user_id, survey_id)
    report = _research_report(db, survey.id)
    if report is None:
        raise HTTPException(status_code=404, detail="Anket araştırma analizi henüz oluşturulmadı")
    return _response(survey, report)


def refresh_survey_research(
    db: Session,
    user_id: int,
    survey_id: int,
) -> SurveyResearchResponse:
    survey = _get_owned_survey(db, user_id, survey_id)
    report = build_and_save_survey_research(db, survey)
    db.commit()
    db.refresh(report)
    return _response(survey, report)


def create_survey_research_ai_summary(
    db: Session,
    user_id: int,
    survey_id: int,
) -> SurveyResearchResponse:
    survey = _get_owned_survey(db, user_id, survey_id)
    report = _research_report(db, survey.id)
    if report is None:
        report = build_and_save_survey_research(db, survey)

    if not is_gemini_configured():
        report.ai_report = None
        report.ai_report_status = "skipped"
        report.ai_report_warning = GEMINI_NOT_CONFIGURED_WARNING
        db.commit()
        db.refresh(report)
        return _response(survey, report)

    research = _response(survey, report)
    payload = research.model_dump(
        include={
            "title",
            "response_count",
            "scored_response_count",
            "likert_question_count",
            "overall_score_100",
            "question_scores",
            "gender_scores",
            "age_scores",
            "neighborhood_scores",
            "quality_issues",
        }
    )
    try:
        _prompt, ai_report = generate_survey_research_summary(payload)
    except Exception:
        report.ai_report = None
        report.ai_report_status = "failed"
        report.ai_report_warning = "Gemini servisi kullanılamadığı için AI özeti oluşturulamadı."
    else:
        report.ai_report = ai_report
        report.ai_report_status = "completed"
        report.ai_report_warning = None

    db.commit()
    db.refresh(report)
    return _response(survey, report)


def build_and_save_survey_research(
    db: Session,
    survey: models.Survey,
) -> models.SurveyReport:
    db.flush()
    questions = (
        db.query(models.SurveyQuestion)
        .filter(models.SurveyQuestion.survey_id == survey.id)
        .order_by(models.SurveyQuestion.order_index)
        .all()
    )
    likert_questions = [question for question in questions if question.is_likert]
    responses = (
        db.query(models.SurveyResponse)
        .filter(models.SurveyResponse.survey_id == survey.id)
        .order_by(models.SurveyResponse.id)
        .all()
    )
    if not responses:
        raise HTTPException(status_code=409, detail="Ankette analiz edilecek cevap bulunamadı")

    answer_map = _answer_map(db, survey.id)
    question_scores = _question_scores(likert_questions, responses, answer_map)
    response_scores = _respondent_scores(likert_questions, responses, answer_map)
    gender_question = _find_demographic_question(questions, "cinsiyet")
    age_question = _find_demographic_question(questions, "yaş", "yas")
    neighborhood_question = _find_demographic_question(questions, "mahalle")

    gender_scores, gender_counts = _demographic_scores(
        responses,
        answer_map,
        response_scores,
        gender_question,
        _normalize_gender,
    )
    age_scores, age_counts = _demographic_scores(
        responses,
        answer_map,
        response_scores,
        age_question,
        _age_band,
    )
    neighborhood_scores, neighborhood_counts, invalid_neighborhoods = _neighborhood_scores(
        responses,
        answer_map,
        response_scores,
        neighborhood_question,
    )

    overall_score = _average(list(response_scores.values()))
    summary = {
        "title": survey.title,
        "response_count": len(responses),
        "scored_response_count": len(response_scores),
        "likert_question_count": len(likert_questions),
        "overall_score_100": overall_score,
        "overall_satisfaction": overall_score,
        "scoring_method": "Likert ortalaması / ölçek üst değeri × 100",
    }
    quality_issues = _quality_issues(
        response_count=len(responses),
        scored_count=len(response_scores),
        question_scores=question_scores,
        gender_question=gender_question,
        gender_count=sum(gender_counts.values()),
        age_question=age_question,
        age_count=sum(age_counts.values()),
        neighborhood_question=neighborhood_question,
        neighborhood_count=sum(neighborhood_counts.values()),
        invalid_neighborhoods=invalid_neighborhoods,
    )
    metrics = {
        "question_scores": question_scores,
        "question_metrics": _legacy_question_metrics(question_scores),
        "gender_scores": gender_scores,
        "age_scores": age_scores,
        "neighborhood_scores": neighborhood_scores,
        "charts": _charts(overall_score, gender_scores, gender_counts, age_scores, age_counts, neighborhood_scores),
        "demographic_sources": {
            "gender": gender_question.column_name if gender_question else None,
            "age": age_question.column_name if age_question else None,
            "neighborhood": neighborhood_question.column_name if neighborhood_question else None,
        },
    }

    report = _research_report(db, survey.id)
    if report is None:
        report = models.SurveyReport(survey_id=survey.id, report_type="research")
        db.add(report)
    report.status = "completed"
    report.summary = _dumps(summary)
    report.metrics = _dumps(metrics)
    report.quality_issues = _dumps(quality_issues)
    report.ai_report = None
    report.ai_report_status = "not_requested"
    report.ai_report_warning = None
    db.flush()
    return report


def _get_owned_survey(db: Session, user_id: int, survey_id: int) -> models.Survey:
    survey = (
        db.query(models.Survey)
        .filter(models.Survey.id == survey_id, models.Survey.user_id == user_id)
        .first()
    )
    if survey is None:
        raise HTTPException(status_code=404, detail="Anket bulunamadı")
    return survey


def _research_report(db: Session, survey_id: int) -> models.SurveyReport | None:
    return (
        db.query(models.SurveyReport)
        .filter(models.SurveyReport.survey_id == survey_id, models.SurveyReport.report_type == "research")
        .order_by(models.SurveyReport.id.desc())
        .first()
    )


def _answer_map(db: Session, survey_id: int) -> dict[int, dict[int, models.SurveyAnswer]]:
    answers = (
        db.query(models.SurveyAnswer)
        .join(models.SurveyResponse, models.SurveyAnswer.response_id == models.SurveyResponse.id)
        .filter(models.SurveyResponse.survey_id == survey_id)
        .all()
    )
    result: dict[int, dict[int, models.SurveyAnswer]] = defaultdict(dict)
    for answer in answers:
        result[answer.response_id][answer.question_id] = answer
    return result


def _question_scores(
    questions: list[models.SurveyQuestion],
    responses: list[models.SurveyResponse],
    answer_map: dict[int, dict[int, models.SurveyAnswer]],
) -> list[dict[str, Any]]:
    items = []
    total = len(responses)
    for question in questions:
        scale_max = _scale_max(question)
        valid_answers = []
        for response in responses:
            answer = answer_map.get(response.id, {}).get(question.id)
            value = _valid_score_value(answer.numeric_value if answer else None, scale_max)
            if value is not None:
                valid_answers.append(value)

        response_count = len(valid_answers)
        missing_count = total - response_count
        options = _loads(question.options, {})
        items.append(
            {
                "question_id": question.id,
                "question_no": question.question_no,
                "column_name": question.column_name,
                "label": question_display_label(question.question_text),
                "question_text": question.question_text,
                "score_100": _score(valid_answers, scale_max),
                "response_count": response_count,
                "missing_count": missing_count,
                "missing_pct": _pct(missing_count, total),
                "distribution": _distribution(valid_answers, options),
            }
        )
    return items


def _respondent_scores(
    questions: list[models.SurveyQuestion],
    responses: list[models.SurveyResponse],
    answer_map: dict[int, dict[int, models.SurveyAnswer]],
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for response in responses:
        question_scores = []
        for question in questions:
            answer = answer_map.get(response.id, {}).get(question.id)
            value = _valid_score_value(answer.numeric_value if answer else None, _scale_max(question))
            if value is not None:
                question_scores.append((value / _scale_max(question)) * 100)
        if question_scores:
            scores[response.id] = round(sum(question_scores) / len(question_scores), 2)
    return scores


def _demographic_scores(
    responses: list[models.SurveyResponse],
    answer_map: dict[int, dict[int, models.SurveyAnswer]],
    response_scores: dict[int, float],
    question: models.SurveyQuestion | None,
    normalizer: Any,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if question is None:
        return [], {}
    values: dict[str, list[float]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    for response in responses:
        if response.id not in response_scores:
            continue
        answer = answer_map.get(response.id, {}).get(question.id)
        label = normalizer(_answer_value(answer))
        if label is None:
            continue
        values[label].append(response_scores[response.id])
        counts[label] += 1
    return _group_scores(values), counts


def _neighborhood_scores(
    responses: list[models.SurveyResponse],
    answer_map: dict[int, dict[int, models.SurveyAnswer]],
    response_scores: dict[int, float],
    question: models.SurveyQuestion | None,
) -> tuple[list[dict[str, Any]], dict[str, int], list[str]]:
    if question is None:
        return [], {}, []
    values: dict[str, list[float]] = defaultdict(list)
    labels: dict[str, str] = {}
    invalid: list[str] = []
    for response in responses:
        if response.id not in response_scores:
            continue
        value = _answer_value(answer_map.get(response.id, {}).get(question.id))
        normalized = _normalize_neighborhood(value)
        if normalized is None:
            if value:
                invalid.append(value)
            continue
        key, label = normalized
        values[key].append(response_scores[response.id])
        labels.setdefault(key, label)
    groups = [
        {
            "label": labels[key],
            "score_100": _average(scores),
            "respondent_count": len(scores),
            "low_sample": len(scores) < MIN_CHART_SAMPLE,
        }
        for key, scores in values.items()
    ]
    groups.sort(key=lambda item: (-item["respondent_count"], item["label"]))
    return groups, {labels[key]: len(scores) for key, scores in values.items()}, invalid


def _group_scores(values: dict[str, list[float]]) -> list[dict[str, Any]]:
    groups = [
        {
            "label": label,
            "score_100": _average(scores),
            "respondent_count": len(scores),
            "low_sample": len(scores) < MIN_CHART_SAMPLE,
        }
        for label, scores in values.items()
    ]
    groups.sort(key=lambda item: (-item["respondent_count"], item["label"]))
    return groups


def _find_demographic_question(
    questions: list[models.SurveyQuestion],
    *keywords: str,
) -> models.SurveyQuestion | None:
    for question in questions:
        text = _fold(question.column_name)
        if question.is_demographic and any(keyword in text for keyword in keywords):
            return question
    return None


def _scale_max(question: models.SurveyQuestion) -> float:
    option_values = []
    for option in _loads(question.options, {}).keys():
        try:
            option_values.append(float(option))
        except (TypeError, ValueError):
            continue
    return max(option_values) if option_values else 5.0


def _valid_score_value(value: float | None, scale_max: float) -> float | None:
    if value is None or value < 1 or value > scale_max:
        return None
    return float(value)


def _score(values: list[float], scale_max: float) -> float | None:
    if not values:
        return None
    return round((sum(values) / len(values) / scale_max) * 100, 2)


def _distribution(values: list[float], options: dict[str, Any]) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        key = str(int(value)) if value.is_integer() else str(value)
        counts[key] += 1
    total = sum(counts.values())
    return [
        {
            "value": key,
            "label": str(options.get(key, key)),
            "count": count,
            "pct": _pct(count, total),
        }
        for key, count in sorted(counts.items(), key=lambda item: float(item[0]))
    ]


def _normalize_gender(value: str | None) -> str | None:
    normalized = _fold(value or "")
    if normalized in {"k", "kadin", "kadın", "female"}:
        return "Kadın"
    if normalized in {"e", "erkek", "male"}:
        return "Erkek"
    return None


def _age_band(value: str | None) -> str | None:
    try:
        age = int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None
    for lower, upper, label in AGE_BANDS:
        if lower <= age <= upper:
            return label
    return None


def _normalize_neighborhood(value: str | None) -> tuple[str, str] | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text or _looks_like_date(text) or re.fullmatch(r"\d+", text):
        return None
    label = re.sub(r"\s+mahallesi?\.?$", "", text, flags=re.IGNORECASE).strip()
    if len(label) < 2:
        return None
    if label.isupper():
        label = label.title()
    return _fold(label), label


def _looks_like_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}", value))


def _answer_value(answer: models.SurveyAnswer | None) -> str | None:
    if answer is None:
        return None
    return answer.option_label or answer.normalized_value or answer.raw_value


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 2) if whole else 0.0


def _quality_issues(
    response_count: int,
    scored_count: int,
    question_scores: list[dict[str, Any]],
    gender_question: models.SurveyQuestion | None,
    gender_count: int,
    age_question: models.SurveyQuestion | None,
    age_count: int,
    neighborhood_question: models.SurveyQuestion | None,
    neighborhood_count: int,
    invalid_neighborhoods: list[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not question_scores:
        issues.append(
            {
                "type": "no_likert_questions",
                "severity": "info",
                "message": "Ankette 100'lük memnuniyet skoru üretilebilecek Likert sorusu bulunamadı.",
            }
        )
    if scored_count < response_count:
        issues.append(
            {
                "type": "unscored_responses",
                "severity": "warning",
                "message": f"{response_count - scored_count} kayıtta puanlanabilir Likert yanıtı yok.",
            }
        )
    for item in question_scores:
        if item["missing_pct"] >= 30:
            issues.append(
                {
                    "type": "high_question_missing_rate",
                    "severity": "warning",
                    "question": item["label"],
                    "message": f"{item['label']} sorusunda eksik yanıt oranı %{item['missing_pct']}.",
                }
            )
    for label, question, count in (
        ("Cinsiyet", gender_question, gender_count),
        ("Yaş", age_question, age_count),
        ("Mahalle", neighborhood_question, neighborhood_count),
    ):
        if question is None:
            issues.append({"type": "missing_demographic", "severity": "info", "message": f"{label} alanı bulunamadı."})
        elif count < scored_count:
            issues.append(
                {
                    "type": "incomplete_demographic",
                    "severity": "info",
                    "message": f"{label} kırılımı puanlanmış {count} katılımcıyı kapsıyor.",
                }
            )
    if invalid_neighborhoods:
        issues.append(
            {
                "type": "invalid_neighborhood",
                "severity": "warning",
                "values": sorted(set(invalid_neighborhoods))[:10],
                "message": "Mahalle alanındaki geçersiz değerler mahalle analizine dahil edilmedi.",
            }
        )
    return issues


def _charts(
    overall_score: float | None,
    gender_scores: list[dict[str, Any]],
    gender_counts: dict[str, int],
    age_scores: list[dict[str, Any]],
    age_counts: dict[str, int],
    neighborhood_scores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    if gender_counts:
        charts.append(_chart("gender-distribution", "donut", "Cinsiyet dağılımı", "count", _count_data(gender_counts)))
    if gender_scores:
        data = [{"label": "Genel", "value": overall_score, "respondent_count": sum(gender_counts.values())}]
        data.extend(_score_data(gender_scores))
        charts.append(_chart("gender-satisfaction", "bar", "Cinsiyete göre memnuniyet", "score_100", data))
    if age_counts:
        charts.append(_chart("age-distribution", "donut", "Yaş dağılımı", "count", _count_data(age_counts, AGE_BANDS)))
    if age_scores:
        data = [{"label": "Genel", "value": overall_score, "respondent_count": sum(age_counts.values())}]
        data.extend(_score_data(age_scores, AGE_BANDS))
        charts.append(_chart("age-satisfaction", "bar", "Yaşa göre memnuniyet", "score_100", data))
    chart_neighborhoods = [item for item in neighborhood_scores if not item["low_sample"]][:15]
    if chart_neighborhoods:
        charts.append(_chart("neighborhood-satisfaction", "bar", "Mahalle bazlı memnuniyet", "score_100", _score_data(chart_neighborhoods)))
    return charts


def _legacy_question_metrics(question_scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keeps the original survey metrics payload usable for existing API consumers."""
    return [
        {
            "column_name": item["column_name"],
            "question_no": item["question_no"],
            "question_text": item["question_text"],
            "question_type": "likert",
            "response_count": item["response_count"],
            "missing_count": item["missing_count"],
            "missing_pct": item["missing_pct"],
            "satisfaction_score": item["score_100"],
            "distribution": item["distribution"],
        }
        for item in question_scores
    ]


def _chart(chart_id: str, chart_type: str, title: str, unit: str, data: list[dict[str, Any]]) -> dict[str, Any]:
    return {"id": chart_id, "type": chart_type, "title": title, "unit": unit, "data": data}


def _score_data(groups: list[dict[str, Any]], order: tuple[tuple[int, int, str], ...] | None = None) -> list[dict[str, Any]]:
    items = [
        {
            "label": group["label"],
            "value": group["score_100"],
            "respondent_count": group["respondent_count"],
            "low_sample": group["low_sample"],
        }
        for group in groups
    ]
    if order is not None:
        positions = {label: index for index, (_, _, label) in enumerate(order)}
        items.sort(key=lambda item: positions.get(item["label"], len(positions)))
    return items


def _count_data(counts: dict[str, int], order: tuple[tuple[int, int, str], ...] | None = None) -> list[dict[str, Any]]:
    items = [{"label": label, "value": value} for label, value in counts.items()]
    if order is not None:
        positions = {label: index for index, (_, _, label) in enumerate(order)}
        items.sort(key=lambda item: positions.get(item["label"], len(positions)))
    else:
        items.sort(key=lambda item: (-item["value"], item["label"]))
    return items


def _response(survey: models.Survey, report: models.SurveyReport) -> SurveyResearchResponse:
    summary = _loads(report.summary, {})
    metrics = _loads(report.metrics, {})
    return SurveyResearchResponse(
        survey_id=survey.id,
        report_id=report.id,
        title=survey.title,
        status=report.status,
        response_count=summary.get("response_count", 0),
        scored_response_count=summary.get("scored_response_count", 0),
        likert_question_count=summary.get("likert_question_count", 0),
        overall_score_100=summary.get("overall_score_100"),
        question_scores=metrics.get("question_scores", []),
        gender_scores=metrics.get("gender_scores", []),
        age_scores=metrics.get("age_scores", []),
        neighborhood_scores=metrics.get("neighborhood_scores", []),
        charts=metrics.get("charts", []),
        quality_issues=_loads(report.quality_issues, []),
        ai_report=report.ai_report,
        ai_report_status=report.ai_report_status,
        ai_report_warning=report.ai_report_warning,
        created_at=report.created_at,
    )


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return ascii_value.casefold()
