import io
import os
from types import SimpleNamespace

os.environ["AUTO_CREATE_TABLES"] = "0"
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "test-key")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///./test_app.db"

from fastapi.testclient import TestClient
from openpyxl import Workbook

from database import Base, SessionLocal, engine
import models  # noqa: F401
from main import app
import ai_analyst


client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def _auth_headers(email: str = "survey@example.com") -> dict[str, str]:
    password = "strong-password"
    register_response = client.post(
        "/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == email

    login_response = client.post(
        "/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_saved_report_generator_uses_a_live_gemini_client(monkeypatch):
    class FakeModels:
        def __init__(self):
            self.calls = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(text="Test Gemini raporu")

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    fake_client = FakeClient()
    monkeypatch.setattr(ai_analyst, "_get_client", lambda: fake_client)
    analysis = SimpleNamespace(
        id=1,
        filename="scores.csv",
        analysis_type="dataset",
        row_count=2,
        column_count=2,
        summary="Iki satirlik test verisi",
        statistics='{"descriptive": []}',
        quality_issues="[]",
    )

    prompt, content = ai_analyst.generate_report_from_analyses([analysis])

    assert analysis.filename in prompt
    assert content == "Test Gemini raporu"
    assert fake_client.models.calls == [
        {"model": ai_analyst.MODEL, "contents": prompt}
    ]


def test_register_rejects_duplicate_email():
    email = "duplicate@example.com"
    response = client.post("/register", json={"email": email, "password": "secret-123"})
    assert response.status_code == 201

    duplicate = client.post("/register", json={"email": email, "password": "secret-123"})
    assert duplicate.status_code == 400


def test_login_rejects_wrong_password():
    email = "wrong-password@example.com"
    client.post("/register", json={"email": email, "password": "correct-123"})

    response = client.post("/login", json={"email": email, "password": "wrong-123"})
    assert response.status_code == 401


def test_auth_normalizes_email_and_returns_current_user():
    email = "normalization@example.com"
    response = client.post(
        "/register",
        json={"email": "  NORMALIZATION@EXAMPLE.COM ", "password": "strong-password"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == email

    login = client.post("/login", json={"email": email, "password": "strong-password"})
    assert login.status_code == 200
    assert login.json()["expires_in"] == 1800

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    current_user = client.get("/users/me", headers=headers)
    assert current_user.status_code == 200
    assert current_user.json()["email"] == email


def test_auth_rejects_invalid_credentials_and_missing_token():
    invalid_email = client.post(
        "/register",
        json={"email": "invalid-email", "password": "strong-password"},
    )
    assert invalid_email.status_code == 422

    short_password = client.post(
        "/register",
        json={"email": "short-password@example.com", "password": "short"},
    )
    assert short_password.status_code == 422

    current_user = client.get("/users/me")
    assert current_user.status_code == 401


def test_cors_allows_local_vite_application():
    response = client.options(
        "/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_upload_general_dataset_saves_source_metadata_and_analysis():
    headers = _auth_headers("general-dataset@example.com")
    csv_content = b"id,city,score\n1,Ankara,10\n2,Izmir,20\n2,Izmir,20\n3,,30\n"

    response = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("scores.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "general"
    assert body["survey_id"] is None
    assert body["row_count"] == 4
    assert body["column_count"] == 3
    assert body["analysis_id"] > 0
    assert any(issue["type"] == "duplicate_rows" for issue in body["quality_issues"])
    assert body["charts"]

    db = SessionLocal()
    try:
        source_file = (
            db.query(models.DatasetFile)
            .filter(models.DatasetFile.dataset_id == body["dataset_id"])
            .one()
        )
        analysis = db.query(models.DataAnalysis).filter(models.DataAnalysis.id == body["analysis_id"]).one()
        assert source_file.content == csv_content
        assert source_file.size_bytes == len(csv_content)
        assert analysis.dataset_id == body["dataset_id"]
        assert analysis.analysis_type == "general"
    finally:
        db.close()


def test_upload_general_xlsx_dataset():
    headers = _auth_headers("general-xlsx@example.com")
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["city", "score"])
    worksheet.append(["Ankara", 10])
    worksheet.append(["Izmir", 20])
    stream = io.BytesIO()
    workbook.save(stream)

    response = client.post(
        "/datasets/upload",
        headers=headers,
        files={
            "file": (
                "scores.xlsx",
                stream.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "general"
    assert body["row_count"] == 2
    assert body["column_count"] == 2


def test_dataset_and_analysis_history_are_paginated_and_user_scoped():
    headers = _auth_headers("dataset-history@example.com")
    csv_content = b"id,city,score\n1,Ankara,10\n2,Izmir,20\n3,Bursa,30\n"
    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("history.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 201
    uploaded = upload.json()

    datasets = client.get("/datasets?offset=0&limit=20", headers=headers)
    assert datasets.status_code == 200
    dataset_list = datasets.json()
    assert dataset_list["total"] >= 1
    assert any(item["id"] == uploaded["dataset_id"] for item in dataset_list["items"])

    detail = client.get(f"/datasets/{uploaded['dataset_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["latest_analysis_id"] == uploaded["analysis_id"]
    assert detail.json()["has_source_file"] is True
    assert len(detail.json()["preview_rows"]) == 3

    rows = client.get(f"/datasets/{uploaded['dataset_id']}/rows?offset=1&limit=1", headers=headers)
    assert rows.status_code == 200
    assert rows.json()["total"] == 3
    assert rows.json()["rows"] == [{"id": 2, "city": "Izmir", "score": 20}]

    downloaded = client.get(f"/datasets/{uploaded['dataset_id']}/download", headers=headers)
    assert downloaded.status_code == 200
    assert downloaded.content == csv_content
    assert "attachment" in downloaded.headers["content-disposition"]

    analyses = client.get("/analyses", headers=headers)
    assert analyses.status_code == 200
    assert any(item["id"] == uploaded["analysis_id"] for item in analyses.json())

    analysis = client.get(f"/analyses/{uploaded['analysis_id']}", headers=headers)
    assert analysis.status_code == 200
    assert analysis.json()["dataset_id"] == uploaded["dataset_id"]
    assert analysis.json()["chart_data"]

    other_headers = _auth_headers("dataset-history-other@example.com")
    assert client.get(f"/datasets/{uploaded['dataset_id']}", headers=other_headers).status_code == 404
    assert client.get(f"/analyses/{uploaded['analysis_id']}", headers=other_headers).status_code == 404


def test_reports_are_created_from_owned_analyses_and_persisted(monkeypatch):
    headers = _auth_headers("report-owner@example.com")

    def upload(filename: str, content: bytes) -> dict:
        response = client.post(
            "/datasets/upload",
            headers=headers,
            files={"file": (filename, content, "text/csv")},
        )
        assert response.status_code == 201
        return response.json()

    first = upload("report-one.csv", b"id,score\n1,10\n2,20\n")
    second = upload("report-two.csv", b"id,score\n1,15\n2,30\n")

    def fake_report_generator(analyses, question):
        assert [analysis.id for analysis in analyses] == [first["analysis_id"], second["analysis_id"]]
        assert question == "Skor farklarini acikla"
        return "structured prompt", "Olusturulan test raporu"

    monkeypatch.setattr("report_service.generate_report_from_analyses", fake_report_generator)
    created = client.post(
        "/reports",
        headers=headers,
        json={
            "analysis_ids": [first["analysis_id"], second["analysis_id"]],
            "title": "Karsilastirma raporu",
            "question": "Skor farklarini acikla",
        },
    )

    assert created.status_code == 201
    report = created.json()
    assert report["title"] == "Karsilastirma raporu"
    assert report["status"] == "completed"
    assert report["analysis_ids"] == [first["analysis_id"], second["analysis_id"]]
    assert report["content"] == "Olusturulan test raporu"

    reports = client.get("/reports", headers=headers)
    assert reports.status_code == 200
    assert any(item["id"] == report["id"] for item in reports.json())

    detail = client.get(f"/reports/{report['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["model_name"]

    duplicate_selection = client.post(
        "/reports",
        headers=headers,
        json={"analysis_ids": [first["analysis_id"], first["analysis_id"]]},
    )
    assert duplicate_selection.status_code == 422

    other_headers = _auth_headers("report-other@example.com")
    assert client.get(f"/reports/{report['id']}", headers=other_headers).status_code == 404
    forbidden_analysis = client.post(
        "/reports",
        headers=other_headers,
        json={"analysis_ids": [first["analysis_id"]]},
    )
    assert forbidden_analysis.status_code == 404


def test_report_generation_failure_is_saved(monkeypatch):
    headers = _auth_headers("report-failure@example.com")
    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("failure.csv", b"id,score\n1,10\n2,20\n", "text/csv")},
    )
    assert upload.status_code == 201

    def failing_report_generator(*_args, **_kwargs):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr("report_service.generate_report_from_analyses", failing_report_generator)
    response = client.post(
        "/reports",
        headers=headers,
        json={"analysis_ids": [upload.json()["analysis_id"]]},
    )
    assert response.status_code == 502

    reports = client.get("/reports", headers=headers)
    assert reports.status_code == 200
    assert reports.json()[0]["status"] == "failed"


def test_upload_dataset_detects_survey_and_returns_survey_summary():
    headers = _auth_headers("unified-survey@example.com")
    csv_content = "\n".join(
        [
            "ANKET ADI: BIRIM MEMNUNIYET ANKETI;;;;",
            'KODLARKEN DIKKAT EDINIZ!;Tarih;"1": Memnun Degilim | "2": Memnunum;Metin',
            "No.;Tarih;1. Hizmetten memnun musunuz?;Gorus ve Oneriler",
            "1;2026-01-01;2;Iyi",
            "2;2026-01-02;1;",
        ]
    ).encode("utf-8")

    response = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("survey.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["detected_format"] == "survey"
    assert body["survey_id"] > 0
    assert body["survey"]["title"] == "BIRIM MEMNUNIYET ANKETI"
    assert body["statistics"]["summary"]["response_count"] == 2
    assert body["charts"]


def test_survey_research_builds_dynamic_question_scores_and_demographics(monkeypatch):
    headers = _auth_headers("survey-research@example.com")
    csv_content = "\n".join(
        [
            "ANKET ADI: SPOR ETKINLIGI MEMNUNIYET ANKETI;;;;;;;",
            'KODLARKEN;Metin;"K": Kadin | "E": Erkek;Sayi;"1": Hic Memnun Degilim | "2": Memnun Degilim | "3": Kararsiz | "4": Memnunum | "5": Cok Memnunum;"1": Hic Memnun Degilim | "2": Memnun Degilim | "3": Kararsiz | "4": Memnunum | "5": Cok Memnunum;;;',
            "No.;Mahalle;Cinsiyet;Yas;1. Katilimdan genel olarak memnuniyetinizi belirtir misiniz?;2. Organizasyon memnuniyetinizi belirtir misiniz? Ortam;;;",
            "1;Konak;K;17;5;4;;;",
            "2;KONAK;E;18;4;5;;;",
            "3;23 Nisan;K;25;3;3;;;",
            "4;23 nisan;K;65;5;5;;;",
            "5;2026-01-30;E;70;5;5;;;",
            "6;;;;;;;",
        ]
    ).encode("utf-8")

    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("research-survey.csv", csv_content, "text/csv")},
    )

    assert upload.status_code == 201
    assert upload.json()["column_count"] == 6
    survey_id = upload.json()["survey_id"]
    research = client.get(f"/surveys/{survey_id}/research", headers=headers)

    assert research.status_code == 200
    body = research.json()
    assert body["title"] == "SPOR ETKINLIGI MEMNUNIYET ANKETI"
    assert body["response_count"] == 6
    assert body["scored_response_count"] == 5
    assert body["overall_score_100"] == 88.0
    assert [item["label"] for item in body["question_scores"]] == [
        "Genel memnuniyet",
        "Ortam",
    ]
    assert [item["score_100"] for item in body["question_scores"]] == [88.0, 88.0]
    assert {item["label"]: item["respondent_count"] for item in body["gender_scores"]} == {
        "Kadın": 3,
        "Erkek": 2,
    }
    assert {item["label"] for item in body["age_scores"]} == {
        "18 yaş altı",
        "18-24",
        "25-34",
        "65+",
    }
    neighborhoods = {item["label"]: item for item in body["neighborhood_scores"]}
    assert neighborhoods["Konak"]["respondent_count"] == 2
    assert neighborhoods["23 Nisan"]["respondent_count"] == 2
    assert any(issue["type"] == "invalid_neighborhood" for issue in body["quality_issues"])

    refreshed = client.post(f"/surveys/{survey_id}/research/refresh", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["report_id"] == body["report_id"]

    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "")
    ai_summary = client.post(f"/surveys/{survey_id}/research/ai-summary", headers=headers)
    assert ai_summary.status_code == 200
    assert ai_summary.json()["ai_report"] is None
    assert ai_summary.json()["ai_report_status"] == "skipped"
    assert ai_summary.json()["scored_response_count"] == 5


def test_upload_dataset_rejects_unsupported_file_type():
    headers = _auth_headers("unsupported-dataset@example.com")
    response = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("dataset.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_dataset_id_creates_multiple_independent_analyses(monkeypatch):
    headers = _auth_headers("dataset-analysis@example.com")
    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "")
    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("scores.csv", b"city,score\nAnkara,10\nIzmir,20\n", "text/csv")},
    )
    assert upload.status_code == 201
    dataset_id = upload.json()["dataset_id"]

    first = client.post(
        f"/datasets/{dataset_id}/analyses",
        headers=headers,
        json={"template": "general", "question": "Ilk inceleme"},
    )
    second = client.post(
        f"/datasets/{dataset_id}/analyses",
        headers=headers,
        json={"template": "general", "question": "Ikinci inceleme"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["dataset_id"] == dataset_id
    assert first.json()["statistics"]
    assert first.json()["ai_report_status"] == "skipped"


def test_dataset_id_analysis_is_user_scoped():
    owner_headers = _auth_headers("dataset-analysis-owner@example.com")
    upload = client.post(
        "/datasets/upload",
        headers=owner_headers,
        files={"file": ("scores.csv", b"city,score\nAnkara,10\n", "text/csv")},
    )
    assert upload.status_code == 201

    other_headers = _auth_headers("dataset-analysis-other@example.com")
    response = client.post(
        f"/datasets/{upload.json()['dataset_id']}/analyses",
        headers=other_headers,
        json={},
    )
    assert response.status_code == 404


def test_survey_detection_reuses_uploaded_dataset_and_is_idempotent():
    headers = _auth_headers("survey-detection@example.com")
    csv_content = "\n".join(
        [
            "ANKET ADI: BIRIM MEMNUNIYET ANKETI;;;;",
            'KODLARKEN DIKKAT EDINIZ!;Tarih;"1": Hayir | "2": Evet;Metin',
            "No.;Tarih;1. Hizmetten memnun musunuz?;Gorus ve Oneriler",
            "1;2026-01-01;2;Iyi",
            "2;2026-01-02;1;",
        ]
    ).encode("utf-8")
    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("survey.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 201
    dataset_id = upload.json()["dataset_id"]
    survey_id = upload.json()["survey_id"]

    response = client.post(f"/datasets/{dataset_id}/detect-survey", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "already_detected"
    assert response.json()["survey_id"] == survey_id


def test_survey_detection_handles_non_survey_and_missing_source_file():
    headers = _auth_headers("survey-detection-general@example.com")
    upload = client.post(
        "/datasets/upload",
        headers=headers,
        files={"file": ("general.csv", b"city,score\nAnkara,10\nIzmir,20\n", "text/csv")},
    )
    assert upload.status_code == 201
    dataset_id = upload.json()["dataset_id"]

    not_survey = client.post(f"/datasets/{dataset_id}/detect-survey", headers=headers)
    assert not_survey.status_code == 200
    assert not_survey.json()["detected"] is False
    assert not_survey.json()["status"] == "not_survey"

    db = SessionLocal()
    try:
        db.query(models.DatasetFile).filter(models.DatasetFile.dataset_id == dataset_id).delete()
        db.commit()
    finally:
        db.close()

    missing_source = client.post(f"/datasets/{dataset_id}/detect-survey", headers=headers)
    assert missing_source.status_code == 409


def test_dataset_comparison_uses_existing_dataset_ids(monkeypatch):
    headers = _auth_headers("dataset-comparison@example.com")
    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "")

    def upload(filename: str, content: bytes) -> int:
        response = client.post(
            "/datasets/upload",
            headers=headers,
            files={"file": (filename, content, "text/csv")},
        )
        assert response.status_code == 201
        return response.json()["dataset_id"]

    first_id = upload("first.csv", b"city,score\nAnkara,10\nIzmir,20\n")
    second_id = upload("second.csv", b"city,score\nAnkara,15\nIzmir,30\n")
    response = client.post(
        "/dataset-comparisons",
        headers=headers,
        json={"dataset_ids": [first_id, second_id]},
    )

    assert response.status_code == 200
    assert response.json()["file1"] == "first.csv"
    assert "Gemini API anahtarı" in response.json()["ai_report"]


def test_analyze_data_skips_ai_report_without_gemini_key(monkeypatch):
    headers = _auth_headers("analyze-no-key@example.com")
    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "")

    def unexpected_ai_call(*_args, **_kwargs):
        raise AssertionError("Gemini cagrisi yapilmamali")

    monkeypatch.setattr("main.strategic_analysis", unexpected_ai_call)
    response = client.post(
        "/analyze/data",
        headers=headers,
        files={"file": ("scores.csv", b"city,score\nAnkara,10\nIzmir,20\n", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["statistics"]
    assert body["ai_report"] is None
    assert body["ai_report_status"] == "skipped"
    assert body["ai_report_warning"] == (
        "Gemini API anahtarı yapılandırılmadığı için AI raporu oluşturulmadı."
    )

    db = SessionLocal()
    try:
        record = db.query(models.DataAnalysis).filter(models.DataAnalysis.id == body["id"]).one()
        assert record.status == "completed"
        assert record.ai_report is None
        assert record.ai_report_status == "skipped"
    finally:
        db.close()

    detail = client.get(f"/analyses/{body['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["ai_report_status"] == "skipped"
    assert detail.json()["ai_report_warning"] == body["ai_report_warning"]


def test_analyze_data_keeps_successful_gemini_behavior(monkeypatch):
    headers = _auth_headers("analyze-with-key@example.com")
    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "configured-key")

    def fake_strategic_analysis(*_args, **_kwargs):
        return "Gemini analiz raporu"

    monkeypatch.setattr("main.strategic_analysis", fake_strategic_analysis)
    response = client.post(
        "/analyze/data",
        headers=headers,
        files={"file": ("scores.csv", b"city,score\nAnkara,10\nIzmir,20\n", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ai_report"] == "Gemini analiz raporu"
    assert body["ai_report_status"] == "completed"
    assert body["ai_report_warning"] is None


def test_analyze_data_preserves_analysis_when_gemini_fails(monkeypatch):
    headers = _auth_headers("analyze-service-failure@example.com")
    monkeypatch.setattr("ai_analyst.GEMINI_API_KEY", "configured-key")

    def failing_strategic_analysis(*_args, **_kwargs):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr("main.strategic_analysis", failing_strategic_analysis)
    response = client.post(
        "/analyze/data",
        headers=headers,
        files={"file": ("scores.csv", b"city,score\nAnkara,10\nIzmir,20\n", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["statistics"]
    assert body["ai_report"] is None
    assert body["ai_report_status"] == "failed"
    assert body["ai_report_warning"] == "Gemini servisi kullanilamadigi icin AI raporu olusturulamadi."

    db = SessionLocal()
    try:
        record = db.query(models.DataAnalysis).filter(models.DataAnalysis.id == body["id"]).one()
        assert record.status == "completed"
        assert record.ai_report_status == "failed"
    finally:
        db.close()


def test_upload_survey_csv_returns_dataset_questions_quality_and_summary():
    headers = _auth_headers()
    csv_content = "\n".join(
        [
            "PAYDAŞ ALGILAMA ANKETLERİ DATA/ANALİZ DOSYASI;;;;;;",
            "ANKET ADI: TEST MÜDÜRLÜĞÜ MEMNUNİYET ANKETİ;;;;;;",
            'KODLARKEN DİKKAT EDİNİZ!;Tarih;"1": Nilüfer | "2": Diğer;"K": Kadın | "E": Erkek;Sayı;"1": Hiç Memnun Değilim | "2": Memnun Değilim | "3": Ne Memnunum, Ne Memnun Değilim | "4": Memnunum | "5": Çok Memnunum;Metin',
            "No.;Tarih;İkamet;Cinsiyet;Yaş;1. Hizmetten genel memnuniyetinizi belirtir misiniz?;Görüş ve Öneriler",
            "1;2026-01-01;1;K;30;5;Çok iyi",
            "2;2026-01-02;2;E;41;4;",
            "3;2026-01-03;1;K;;3;Daha hızlı olabilir",
        ]
    ).encode("utf-8")

    response = client.post(
        "/surveys/upload",
        headers=headers,
        files={"file": ("survey.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["dataset_id"] > 0
    assert body["survey_id"] > 0
    assert body["title"] == "TEST MÜDÜRLÜĞÜ MEMNUNİYET ANKETİ"
    assert body["row_count"] == 3
    assert body["column_count"] == 7
    assert body["header_row"] == 4
    assert body["data_start_row"] == 5
    assert len(body["columns"]) == 7
    assert len(body["questions"]) == 7

    satisfaction_questions = [
        question for question in body["questions"] if question["is_likert"]
    ]
    assert len(satisfaction_questions) == 1
    assert body["report"]["summary"]["overall_satisfaction"] == 80.0
    assert "quality_issues" in body["report"]

    detail_response = client.get(f"/surveys/{body['survey_id']}", headers=headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == body["survey_id"]
    assert detail["dataset_id"] == body["dataset_id"]
    assert detail["report"]["summary"]["response_count"] == 3


def test_upload_survey_rejects_unsupported_file_type():
    headers = _auth_headers("unsupported@example.com")
    response = client.post(
        "/surveys/upload",
        headers=headers,
        files={"file": ("survey.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
