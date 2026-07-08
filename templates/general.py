"""
GeneralTemplate — Genel Keşifsel Veri Analizi (EDA) Şablonu
=============================================================
Her veri seti türü için kullanılabilecek kapsamlı analiz şablonu.
"""

from __future__ import annotations

from data_ingestor import IngestedData
from stats_engine import StatisticsResult
from templates.base import BaseTemplate


class GeneralTemplate(BaseTemplate):

    name = "general"
    description = "Genel keşifsel veri analizi (EDA)"

    def build_prompt(
        self,
        ingested: IngestedData,
        stats: StatisticsResult,
        question: str | None = None,
    ) -> str:
        # Sütun bilgisi
        columns_desc = "\n".join(
            f"  - {c.name} ({c.dtype}, {c.unique_count} benzersiz"
            f"{f', %{c.missing_pct} eksik' if c.missing_count > 0 else ''})"
            for c in ingested.columns
        )

        # Ana prompt
        prompt = f"""Sen kıdemli bir veri analistisin. Aşağıdaki veri setinin istatistiksel özetini inceleyerek stratejik bir analiz raporu hazırla. Raporunu Türkçe yaz.

VERİ SETİ BİLGİSİ:
- Dosya adı: {ingested.filename}
- Boyut: {ingested.row_count} satır × {ingested.column_count} sütun
- Sütunlar:
{columns_desc}

TANIMLAYICI İSTATİSTİKLER:
{self._format_descriptive_table(stats)}

KORELASYON ANALİZİ (güçlü ilişkiler):
{self._format_correlations(stats)}

AYKIRI DEĞER TESPİTİ:
{self._format_outliers(stats)}

KATEGORİK DAĞILIMLAR:
{self._format_categories(stats)}

GRUP KARŞILAŞTIRMALARI:
{self._format_groups(stats)}

EKSİK VERİ DURUMU:
{self._format_missing(stats)}

Lütfen raporunu aşağıdaki bölümlerle yapılandır:

1. ANAHTAR BULGULAR
En önemli 3-5 bulguyu madde halinde yaz. Rakamlarla destekle.

2. ANOMALİLER VE RİSKLER
Dikkat edilmesi gereken anormal durumlar, aykırı değerler ve potansiyel veri kalitesi sorunları.

3. İLİŞKİ ANALİZİ
Değişkenler arasındaki anlamlı bağlantılar ve bunların olası nedenleri.

4. STRATEJİK ÖNERİLER
Veriye dayalı, uygulanabilir aksiyon önerileri. Her öneri için gerekçe belirt.

5. SONRAKI ADIMLAR
Derinlemesine incelenmesi gereken alanlar ve önerilen ek analizler."""

        # Kullanıcının özel sorusu varsa ekle
        if question:
            prompt += f"""

KULLANICININ ÖZEL SORUSU:
{question}

Yukarıdaki bölümlere ek olarak, kullanıcının sorusunu da veriye dayalı olarak yanıtla. Yanıtını "6. KULLANICI SORUSUNA YANIT" başlığı altında ver."""

        return prompt
