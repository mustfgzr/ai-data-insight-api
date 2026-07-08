"""
İstatistik Motoru
==================
pandas DataFrame üzerinde otomatik istatistiksel analiz yapar.
Tanımlayıcı istatistikler, korelasyon, aykırı değer, frekans ve grup karşılaştırması.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as sp_stats


# ── Sonuç Veri Yapıları ──────────────────────────────────────

@dataclass
class DescriptiveStats:
    """Bir sayısal sütunun tanımlayıcı istatistikleri."""
    column: str
    count: int
    mean: float
    median: float
    std: float
    min: float
    max: float
    q1: float
    q3: float
    iqr: float
    skewness: float
    kurtosis: float


@dataclass
class Correlation:
    """İki sütun arasındaki korelasyon."""
    col1: str
    col2: str
    pearson_r: float
    strength: str   # "güçlü pozitif", "orta negatif", vb.


@dataclass
class OutlierInfo:
    """Bir sütundaki aykırı değer bilgisi."""
    column: str
    outlier_count: int
    outlier_pct: float
    lower_bound: float
    upper_bound: float


@dataclass
class CategoryDistribution:
    """Kategorik sütun değer dağılımı."""
    column: str
    unique_count: int
    top_values: list[dict]  # [{"value": "X", "count": 50, "pct": 25.0}, ...]


@dataclass
class GroupComparison:
    """Kategorik sütuna göre sayısal sütun karşılaştırması."""
    group_column: str
    value_column: str
    groups: list[dict]  # [{"group": "A", "mean": 10.5, "median": 9.0, "count": 50}, ...]


@dataclass
class StatisticsResult:
    """Tüm istatistiksel analiz sonuçları."""
    descriptive: list[DescriptiveStats] = field(default_factory=list)
    correlations: list[Correlation] = field(default_factory=list)
    strong_correlations: list[Correlation] = field(default_factory=list)
    outliers: list[OutlierInfo] = field(default_factory=list)
    category_distributions: list[CategoryDistribution] = field(default_factory=list)
    group_comparisons: list[GroupComparison] = field(default_factory=list)
    missing_summary: dict = field(default_factory=dict)


# ── Ana Analiz Fonksiyonu ─────────────────────────────────────

def analyze(df: pd.DataFrame) -> StatisticsResult:
    """DataFrame üzerinde kapsamlı istatistiksel analiz yapar."""
    result = StatisticsResult()

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    # 1. Tanımlayıcı istatistikler
    result.descriptive = _descriptive_stats(df, numeric_cols)

    # 2. Korelasyon matrisi
    result.correlations, result.strong_correlations = _correlations(df, numeric_cols)

    # 3. Aykırı değer tespiti
    result.outliers = _outlier_detection(df, numeric_cols)

    # 4. Kategorik dağılımlar
    result.category_distributions = _category_distributions(df, categorical_cols)

    # 5. Grup karşılaştırmaları (en iyi kategorik × sayısal çift)
    result.group_comparisons = _group_comparisons(df, numeric_cols, categorical_cols)

    # 6. Eksik veri özeti
    result.missing_summary = _missing_summary(df)

    return result


# ── Alt Analiz Fonksiyonları ──────────────────────────────────

def _descriptive_stats(df: pd.DataFrame, numeric_cols: list[str]) -> list[DescriptiveStats]:
    """Her sayısal sütun için tanımlayıcı istatistikleri hesaplar."""
    results = []
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))

        results.append(DescriptiveStats(
            column=col,
            count=int(series.count()),
            mean=round(float(series.mean()), 4),
            median=round(float(series.median()), 4),
            std=round(float(series.std()), 4),
            min=round(float(series.min()), 4),
            max=round(float(series.max()), 4),
            q1=round(q1, 4),
            q3=round(q3, 4),
            iqr=round(q3 - q1, 4),
            skewness=round(float(sp_stats.skew(series)), 4),
            kurtosis=round(float(sp_stats.kurtosis(series)), 4),
        ))
    return results


def _correlations(
    df: pd.DataFrame, numeric_cols: list[str]
) -> tuple[list[Correlation], list[Correlation]]:
    """Korelasyon matrisi hesaplar ve güçlü korelasyonları filtreler."""
    all_corrs = []
    strong_corrs = []

    if len(numeric_cols) < 2:
        return all_corrs, strong_corrs

    corr_matrix = df[numeric_cols].corr(method="pearson")

    # Üst üçgeni al (tekrarı önle)
    for i, col1 in enumerate(numeric_cols):
        for col2 in numeric_cols[i + 1:]:
            r = corr_matrix.loc[col1, col2]
            if pd.isna(r):
                continue

            r = round(float(r), 4)
            strength = _correlation_strength(r)

            corr = Correlation(col1=col1, col2=col2, pearson_r=r, strength=strength)
            all_corrs.append(corr)

            if abs(r) >= 0.7:
                strong_corrs.append(corr)

    # Güçlüden zayıfa sırala
    strong_corrs.sort(key=lambda c: abs(c.pearson_r), reverse=True)
    return all_corrs, strong_corrs


def _correlation_strength(r: float) -> str:
    """Korelasyon katsayısını sözel ifadeye çevirir."""
    abs_r = abs(r)
    if abs_r >= 0.9:
        level = "çok güçlü"
    elif abs_r >= 0.7:
        level = "güçlü"
    elif abs_r >= 0.5:
        level = "orta"
    elif abs_r >= 0.3:
        level = "zayıf"
    else:
        level = "çok zayıf"

    direction = "pozitif" if r > 0 else "negatif"
    return f"{level} {direction}"


def _outlier_detection(df: pd.DataFrame, numeric_cols: list[str]) -> list[OutlierInfo]:
    """IQR yöntemiyle aykırı değerleri tespit eder."""
    results = []
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty or len(series) < 4:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())

        if outlier_count > 0:
            results.append(OutlierInfo(
                column=col,
                outlier_count=outlier_count,
                outlier_pct=round((outlier_count / len(series)) * 100, 1),
                lower_bound=round(lower, 4),
                upper_bound=round(upper, 4),
            ))
    return results


def _category_distributions(
    df: pd.DataFrame, categorical_cols: list[str]
) -> list[CategoryDistribution]:
    """Kategorik sütunlar için değer dağılımlarını hesaplar."""
    results = []
    for col in categorical_cols:
        if col.startswith("_"):  # _sheet_name gibi iç sütunları atla
            continue

        series = df[col].dropna()
        if series.empty:
            continue

        value_counts = series.value_counts().head(10)
        total = len(series)
        top_values = [
            {
                "value": str(val),
                "count": int(count),
                "pct": round((count / total) * 100, 1),
            }
            for val, count in value_counts.items()
        ]

        results.append(CategoryDistribution(
            column=col,
            unique_count=int(series.nunique()),
            top_values=top_values,
        ))
    return results


def _group_comparisons(
    df: pd.DataFrame,
    numeric_cols: list[str],
    categorical_cols: list[str],
    max_comparisons: int = 3,
) -> list[GroupComparison]:
    """En uygun kategorik × sayısal çiftleri için grup karşılaştırmaları yapar."""
    results = []

    # Düşük kardinaliteli kategorik sütunları seç (2-15 arası benzersiz değer)
    good_cats = [
        c for c in categorical_cols
        if not c.startswith("_") and 2 <= df[c].nunique() <= 15
    ]

    if not good_cats or not numeric_cols:
        return results

    # İlk birkaç uygun çift için karşılaştırma yap
    count = 0
    for cat_col in good_cats:
        for num_col in numeric_cols:
            if count >= max_comparisons:
                break

            grouped = df.groupby(cat_col)[num_col].agg(["mean", "median", "count"])
            groups = [
                {
                    "group": str(idx),
                    "mean": round(float(row["mean"]), 4),
                    "median": round(float(row["median"]), 4),
                    "count": int(row["count"]),
                }
                for idx, row in grouped.iterrows()
                if not pd.isna(row["mean"])
            ]

            if groups:
                results.append(GroupComparison(
                    group_column=cat_col,
                    value_column=num_col,
                    groups=groups,
                ))
                count += 1
        if count >= max_comparisons:
            break

    return results


def _missing_summary(df: pd.DataFrame) -> dict:
    """Eksik veri özeti üretir."""
    missing = df.isna().sum()
    total = len(df)
    cols_with_missing = {
        str(col): {
            "count": int(count),
            "pct": round((count / total) * 100, 1),
        }
        for col, count in missing.items()
        if count > 0
    }
    return {
        "total_cells": int(df.size),
        "total_missing": int(missing.sum()),
        "total_missing_pct": round((missing.sum() / df.size) * 100, 2) if df.size > 0 else 0,
        "columns_with_missing": cols_with_missing,
    }


# ── Serileştirme Yardımcıları ─────────────────────────────────

def result_to_dict(result: StatisticsResult) -> dict:
    """StatisticsResult'ı JSON-serileştirilebilir dict'e dönüştürür."""
    from dataclasses import asdict
    return {
        "descriptive": [asdict(d) for d in result.descriptive],
        "correlations": [asdict(c) for c in result.correlations],
        "strong_correlations": [asdict(c) for c in result.strong_correlations],
        "outliers": [asdict(o) for o in result.outliers],
        "category_distributions": [asdict(cd) for cd in result.category_distributions],
        "group_comparisons": [asdict(gc) for gc in result.group_comparisons],
        "missing_summary": result.missing_summary,
    }
