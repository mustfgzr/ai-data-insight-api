"""
BaseTemplate — Tüm analiz şablonlarının miras alacağı soyut sınıf.
================================================================
Yeni bir şablon oluşturmak için bu sınıfı miras alın ve
build_prompt() metodunu override edin.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from data_ingestor import IngestedData
from stats_engine import StatisticsResult


class BaseTemplate(ABC):
    """Analiz şablonu arayüzü."""

    name: str = "base"
    description: str = "Temel şablon"

    @abstractmethod
    def build_prompt(
        self,
        ingested: IngestedData,
        stats: StatisticsResult,
        question: str | None = None,
    ) -> str:
        """
        Gemini'a gönderilecek prompt'u oluşturur.

        Args:
            ingested: Ayrıştırılmış veri metadata'sı
            stats: İstatistiksel analiz sonuçları
            question: Kullanıcının opsiyonel özel sorusu

        Returns:
            Gemini'a gönderilecek tam prompt metni
        """
        ...

    def _format_descriptive_table(self, stats: StatisticsResult) -> str:
        """Tanımlayıcı istatistikleri tablo formatında döndürür."""
        if not stats.descriptive:
            return "Sayısal sütun bulunamadı."

        lines = ["Sütun | Ort | Medyan | Std | Min | Max | Çarpıklık"]
        lines.append("--- | --- | --- | --- | --- | --- | ---")
        for d in stats.descriptive:
            lines.append(
                f"{d.column} | {d.mean} | {d.median} | {d.std} | "
                f"{d.min} | {d.max} | {d.skewness}"
            )
        return "\n".join(lines)

    def _format_correlations(self, stats: StatisticsResult) -> str:
        """Güçlü korelasyonları formatlar."""
        if not stats.strong_correlations:
            return "Güçlü korelasyon (|r| >= 0.7) bulunamadı."

        lines = []
        for c in stats.strong_correlations:
            lines.append(f"- {c.col1} <-> {c.col2}: r={c.pearson_r} ({c.strength})")
        return "\n".join(lines)

    def _format_outliers(self, stats: StatisticsResult) -> str:
        """Aykırı değer özetini formatlar."""
        if not stats.outliers:
            return "Aykırı değer tespit edilmedi."

        lines = []
        for o in stats.outliers:
            lines.append(
                f"- {o.column}: {o.outlier_count} aykırı değer (%{o.outlier_pct}), "
                f"alt sınır={o.lower_bound}, üst sınır={o.upper_bound}"
            )
        return "\n".join(lines)

    def _format_categories(self, stats: StatisticsResult) -> str:
        """Kategorik dağılımları formatlar."""
        if not stats.category_distributions:
            return "Kategorik sütun bulunamadı."

        lines = []
        for cd in stats.category_distributions:
            top = ", ".join(
                [f"{v['value']}({v['count']}, %{v['pct']})" for v in cd.top_values[:5]]
            )
            lines.append(f"- {cd.column} ({cd.unique_count} benzersiz): {top}")
        return "\n".join(lines)

    def _format_groups(self, stats: StatisticsResult) -> str:
        """Grup karşılaştırmalarını formatlar."""
        if not stats.group_comparisons:
            return "Grup karşılaştırması yapılamadı."

        lines = []
        for gc in stats.group_comparisons:
            lines.append(f"\n{gc.group_column} bazında {gc.value_column}:")
            for g in gc.groups:
                lines.append(
                    f"  - {g['group']}: ort={g['mean']}, med={g['median']}, n={g['count']}"
                )
        return "\n".join(lines)

    def _format_missing(self, stats: StatisticsResult) -> str:
        """Eksik veri özetini formatlar."""
        ms = stats.missing_summary
        if not ms or ms.get("total_missing", 0) == 0:
            return "Eksik veri yok."

        lines = [f"Toplam: {ms['total_missing']}/{ms['total_cells']} (%{ms['total_missing_pct']})"]
        for col, info in ms.get("columns_with_missing", {}).items():
            lines.append(f"- {col}: {info['count']} eksik (%{info['pct']})")
        return "\n".join(lines)
