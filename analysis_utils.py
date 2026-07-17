from __future__ import annotations

from typing import Any

import pandas as pd

from data_ingestor import ColumnInfo


def build_data_quality_issues(df: pd.DataFrame, columns: list[ColumnInfo]) -> list[dict[str, Any]]:
    """Genel veri setleri için frontend'e uygun veri kalitesi uyarıları üretir."""
    issues: list[dict[str, Any]] = []

    for column in columns:
        if column.missing_pct >= 30:
            issues.append(
                {
                    "type": "high_missing_rate",
                    "severity": "warning",
                    "column": column.name,
                    "message": f"{column.name} kolonunda eksik veri oranı %{column.missing_pct}",
                }
            )

    duplicate_rows = int(df.duplicated().sum())
    if duplicate_rows:
        issues.append(
            {
                "type": "duplicate_rows",
                "severity": "warning",
                "count": duplicate_rows,
                "message": f"{duplicate_rows} tekrar eden satır bulundu",
            }
        )

    return issues


def build_chart_data(statistics: dict[str, Any]) -> list[dict[str, Any]]:
    """İstatistik sonuçlarını UI'da doğrudan çizilebilecek basit grafik serilerine dönüştürür."""
    charts: list[dict[str, Any]] = []

    for distribution in statistics.get("category_distributions", []):
        values = distribution.get("top_values", [])
        if not values:
            continue
        charts.append(
            {
                "type": "bar",
                "title": f"{distribution['column']} dağılımı",
                "column": distribution["column"],
                "labels": [item["value"] for item in values],
                "series": [{"name": "Kayıt", "data": [item["count"] for item in values]}],
            }
        )

    missing_columns = statistics.get("missing_summary", {}).get("columns_with_missing", {})
    if missing_columns:
        charts.append(
            {
                "type": "bar",
                "title": "Eksik veri oranları",
                "column": None,
                "labels": list(missing_columns.keys()),
                "series": [
                    {
                        "name": "Eksik %",
                        "data": [item["pct"] for item in missing_columns.values()],
                    }
                ],
            }
        )

    return charts


def build_survey_chart_data(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []
    for metric in metrics.get("question_metrics", []):
        distribution = metric.get("distribution", [])
        if not distribution:
            continue
        charts.append(
            {
                "type": "bar",
                "title": metric.get("question_text") or metric["column_name"],
                "column": metric["column_name"],
                "labels": [item["label"] for item in distribution],
                "series": [{"name": "Yanıt", "data": [item["count"] for item in distribution]}],
            }
        )
    return charts


def build_data_summary(row_count: int, column_count: int, quality_issues: list[dict[str, Any]]) -> str:
    return (
        f"{row_count} satır ve {column_count} kolon işlendi. "
        f"Veri kalite uyarısı sayısı {len(quality_issues)}."
    )
