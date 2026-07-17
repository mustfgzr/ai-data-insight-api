# Data Insight API

Data Insight, CSV ve XLSX dosyalarini kullanici bazli olarak saklayan, kolon yapisini ve veri kalitesini cikaran, anket yapisini tanimlayan ve kayitli analizlerden Gemini raporu uretebilen bir FastAPI + React MVP'sidir.

## MVP Akisi

1. Kullanici `POST /register` ve `POST /login` ile JWT oturumu acar.
2. `POST /datasets/upload` CSV veya XLSX dosyasini okur, dataset, kaynak dosya, kolon metadata, satirlar ve otomatik analizi kaydeder.
3. Arayuz veri setlerini, satir onizlemesini, kalite uyarilarini ve grafik verilerini gosterir.
4. Kullanici bir ila bes analizi secer; `POST /reports` bu analizlerin yapilandirilmis istatistikleriyle Gemini raporu olusturur ve kaydeder.

## Yerelde Calistirma

Python 3.12+ ve Node.js 20.19+ gereklidir.

```powershell
cd "C:\Users\mst\Desktop\data analysis api\ai-data-insight-api"
Copy-Item .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Ikinci bir terminalde:

```powershell
cd "C:\Users\mst\Desktop\data analysis api\ai-data-insight-api\frontend"
Copy-Item .env.example .env
pnpm install
pnpm dev
```

Arayuz `http://127.0.0.1:5173`, API ise `http://127.0.0.1:8000` adresinde calisir. Frontend `.env` dosyasinda `VITE_API_BASE_URL` ile farkli API adresi tanimlanabilir.

## Gemini Yapilandirmasi

Temel kayit, giris, dosya yukleme ve otomatik veri analizi Gemini anahtari olmadan calisir. Rapor olusturmak icin backend `.env` dosyasina gecerli bir `GEMINI_API_KEY` eklenmelidir. Uretim ortaminda `SECRET_KEY` de guvenli, rastgele bir deger olmalidir.

## Temel API Uclari

| Amac | Uc |
| --- | --- |
| Kayit ve giris | `POST /register`, `POST /login`, `GET /users/me` |
| Dataset yukleme | `POST /datasets/upload` |
| Dataset gecmisi | `GET /datasets`, `GET /datasets/{id}`, `GET /datasets/{id}/rows` |
| Kaynak indirme | `GET /datasets/{id}/download` |
| Analiz gecmisi | `GET /analyses`, `GET /analyses/{id}` |
| Gemini raporlari | `POST /reports`, `GET /reports`, `GET /reports/{id}` |

Korumali uclara `Authorization: Bearer <JWT>` basligi gerekir.

## Kontroller

```powershell
python -m pytest -q -p no:cacheprovider
cd frontend
pnpm build
```

Testler kayit/giris, yetkilendirme, migration, CSV/XLSX yukleme, anket algilama, dataset sorgulama ve kayitli rapor akisini kapsar.
