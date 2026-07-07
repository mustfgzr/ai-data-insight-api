import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)


def summarize_text(text: str) -> str:
    """Metni Gemini 3.1 Flash-Lite modeline gönderir ve Türkçe özet alır."""
    # Çok uzun metinleri kırp (token limitlerine karşı güvenlik)
    max_chars = 50_000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... metin kırpıldı ...]"

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"Aşağıdaki metni Türkçe olarak detaylı bir şekilde özetle:\n\n{text}",
    )

    return response.text.strip()
