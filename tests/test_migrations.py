from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


EXPECTED_TABLES = {
    "users",
    "analyses",
    "data_analyses",
    "datasets",
    "dataset_files",
    "dataset_columns",
    "dataset_rows",
    "surveys",
    "survey_questions",
    "survey_responses",
    "survey_answers",
    "survey_reports",
    "reports",
    "report_analyses",
}


def test_alembic_upgrade_and_downgrade_create_expected_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "migration_test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", database_url)

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert EXPECTED_TABLES.issubset(inspect(engine).get_table_names())

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
