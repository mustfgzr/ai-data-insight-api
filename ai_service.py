import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _get_client() -> genai.Client:
    """Gemini istemcisini yalnizca AI endpoint'i cagirildiginda olusturur."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY ayarlanmadan AI ozetleri olusturulamaz")
    return genai.Client(api_key=GEMINI_API_KEY)


def summarize_text(text: str) -> str:
    """Metni Gemini 3.1 Flash-Lite modeline gönderir ve Türkçe özet alır."""
    # Çok uzun metinleri kırp (token limitlerine karşı güvenlik)
    max_chars = 50_000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... metin kırpıldı ...]"

    client = _get_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"Aşağıdaki metni Türkçe olarak detaylı bir şekilde özetle:\n\n{text}",
    )

    return response.text.strip()
