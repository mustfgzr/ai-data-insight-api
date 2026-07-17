"""
Gemini Stratejik Yorumlayıcı
==============================
İstatistik sonuçlarını şablon sistemine göre prompt'a dönüştürüp
Gemini API'ye gönderir ve yapılandırılmış analiz raporu alır.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai

from data_ingestor import IngestedData
from stats_engine import StatisticsResult
from templates import get_template

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL = "gemini-3.1-flash-lite"


def generate_report_from_analyses(
    analyses: list[object],
    question: str | None = None,
) -> tuple[str, str]:
    """Kayıtlı analizlerin yalnızca yapılandırılmış özetleriyle Gemini raporu üretir."""
    snapshots = []
    for analysis in analyses:
        statistics = _loads_json(getattr(analysis, "statistics", None), {})
        quality_issues = _loads_json(getattr(analysis, "quality_issues", None), [])
        if not isinstance(statistics, dict):
            statistics = {}
        if not isinstance(quality_issues, list):
            quality_issues = []
        snapshots.append(
            {
                "analysis_id": getattr(analysis, "id"),
                "filename": getattr(analysis, "filename"),
                "analysis_type": getattr(analysis, "analysis_type", None),
                "row_count": getattr(analysis, "row_count", None),
                "column_count": getattr(analysis, "column_count", None),
                "summary": getattr(analysis, "summary", None),
                "descriptive": statistics.get("descriptive", [])[:20],
                "strong_correlations": statistics.get("strong_correlations", [])[:20],
                "category_distributions": statistics.get("category_distributions", [])[:20],
                "missing_summary": statistics.get("missing_summary", {}),
                "survey_summary": statistics.get("summary", {}),
                "survey_metrics": statistics.get("metrics", {}).get("question_metrics", [])[:30],
                "quality_issues": quality_issues[:20],
            }
        )

    prompt = f"""Sen kıdemli bir veri analistisin. Aşağıdaki yapılandırılmış analiz özetlerini kullanarak Türkçe, açıklayıcı ve veriye dayalı bir rapor hazırla.

Kurallar:
- Ham satır verisi verilmemiştir; yalnızca sağlanan istatistiklere dayan.
- Kesin olmayan çıkarımları açıkça ihtiyatlı biçimde belirt.
- Raporu şu başlıklarla yaz: Genel Özet, Önemli Bulgular, Veri Kalitesi, Karşılaştırma, Öneriler.

ANALİZ ÖZETLERİ:
{json.dumps(snapshots, ensure_ascii=False, default=str)}"""

    if question:
        prompt += f"\n\nKULLANICININ ODAK SORUSU:\n{question}"

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return prompt, response.text.strip()


def strategic_analysis(
    ingested: IngestedData,
    stats: StatisticsResult,
    template_name: str = "general",
    question: str | None = None,
) -> str:
    """
    Veri seti istatistiklerini Gemini'a gönderip stratejik analiz raporu alır.

    Args:
        ingested: Ayrıştırılmış veri metadata'sı
        stats: İstatistiksel analiz sonuçları
        template_name: Kullanılacak şablon adı
        question: Kullanıcının opsiyonel özel sorusu

    Returns:
        Gemini'dan gelen stratejik analiz raporu (metin)
    """
    # Şablonu al ve prompt oluştur
    template = get_template(template_name)
    prompt = template.build_prompt(ingested, stats, question)

    # Gemini'a gönder
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    return response.text.strip()


def compare_datasets(
    ingested1: IngestedData,
    stats1: StatisticsResult,
    ingested2: IngestedData,
    stats2: StatisticsResult,
    question: str | None = None,
) -> str:
    """
    İki veri setini karşılaştıran Gemini analizi.

    Args:
        ingested1, stats1: Birinci veri seti
        ingested2, stats2: İkinci veri seti
        question: Kullanıcının opsiyonel sorusu

    Returns:
        Karşılaştırma raporu
    """
    template = get_template("general")

    # İki veri seti için özet bilgileri hazırla
    def _summarize(ingested: IngestedData, stats: StatisticsResult) -> str:
        return f"""Dosya: {ingested.filename}
Boyut: {ingested.row_count} satır × {ingested.column_count} sütun

Tanımlayıcı İstatistikler:
{template._format_descriptive_table(stats)}

Güçlü Korelasyonlar:
{template._format_correlations(stats)}

Aykırı Değerler:
{template._format_outliers(stats)}

Kategorik Dağılımlar:
{template._format_categories(stats)}

Grup Karşılaştırmaları:
{template._format_groups(stats)}"""

    prompt = f"""Sen kıdemli bir veri analistisin. Aşağıdaki iki veri setini karşılaştırarak detaylı bir analiz raporu hazırla. Raporunu Türkçe yaz.

═══════════════════════════════════════
VERİ SETİ 1: {ingested1.filename}
═══════════════════════════════════════
{_summarize(ingested1, stats1)}

═══════════════════════════════════════
VERİ SETİ 2: {ingested2.filename}
═══════════════════════════════════════
{_summarize(ingested2, stats2)}

Lütfen raporunu aşağıdaki bölümlerle yapılandır:

1. GENEL KARŞILAŞTIRMA
İki veri setinin boyut, yapı ve genel istatistik farkları.

2. ÖNEMLİ DEĞİŞİMLER
İki set arasındaki en dikkat çekici farklılıklar. Artış/azalış yüzdeleri ile.

3. TREND ANALİZİ
Veriler bir zaman dilimini temsil ediyorsa, gözlemlenen trendler.

4. RİSK VE FIRSATLAR
Değişimlerin işaret ettiği riskler ve fırsatlar.

5. STRATEJİK ÖNERİLER
Karşılaştırmaya dayalı aksiyon önerileri."""

    if question:
        prompt += f"""

KULLANICININ SORUSU:
{question}

Yukarıdaki bölümlere ek olarak, bu soruyu "6. KULLANICI SORUSUNA YANIT" başlığında yanıtla."""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def ask_about_data(
    ingested: IngestedData,
    stats: StatisticsResult,
    question: str,
) -> str:
    """
    Kullanıcının doğal dil sorusunu veri bağlamında yanıtlar.

    Args:
        ingested: Ayrıştırılmış veri
        stats: İstatistiksel analiz sonuçları
        question: Kullanıcının sorusu

    Returns:
        Veriye dayalı yanıt
    """
    template = get_template("general")

    # Veri önizlemesi (ilk 10 satır)
    preview_rows = ingested.preview_head[:5]
    preview_str = "\n".join([str(row) for row in preview_rows])

    prompt = f"""Sen bir veri analisti asistanısın. Kullanıcının sorusunu aşağıdaki veri seti bağlamında yanıtla. Türkçe yanıt ver.

VERİ SETİ: {ingested.filename}
Boyut: {ingested.row_count} satır × {ingested.column_count} sütun

Sütunlar ve tipleri:
{chr(10).join(f'  - {c.name} ({c.dtype})' for c in ingested.columns)}

Veri Önizleme (ilk 5 satır):
{preview_str}

İstatistiksel Özet:
{template._format_descriptive_table(stats)}

Kategorik Dağılımlar:
{template._format_categories(stats)}

Grup Karşılaştırmaları:
{template._format_groups(stats)}

KULLANICININ SORUSU: {question}

Yanıtını şu şekilde yapılandır:
1. YANIT: Sorunun doğrudan, net cevabı
2. DESTEKLEYEN VERİ: Yanıtı destekleyen sayısal kanıtlar
3. EK NOTLAR: Soruyla ilgili dikkat çekmek istediğin ek bilgiler"""

    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def _loads_json(value: str | None, default: object) -> object:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
