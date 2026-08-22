# Backend

Minimal FastAPI backend for the Airport Investment Agent.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive docs at `/docs`
and a health check at `/api/v1/health`.

`requirements.txt` contains runtime-only dependencies for the Docker image.
`requirements-dev.txt` adds the test and offline data-build dependencies.

## Configuration

Copy `.env.example` to `.env` and adjust it as needed. Important settings:

- `CORS_ALLOWED_ORIGINS`: comma-separated frontend origins.
- `AIRPORT_DATABASE_FILE`: path to the immutable SQLite snapshot.
- `AERODATABOX_API_KEY`: optional RapidAPI secret for live enrichment.
- `USE_AERODATABOX`: disables all live calls when set to `false`.
