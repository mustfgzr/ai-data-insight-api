import os

os.environ["AUTO_CREATE_TABLES"] = "0"
os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "test-key")
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SQLALCHEMY_DATABASE_URL"] = "sqlite:///./test_app.db"

from fastapi.testclient import TestClient

from database import Base, engine
import models  # noqa: F401
from main import app


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
