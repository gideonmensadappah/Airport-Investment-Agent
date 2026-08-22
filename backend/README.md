# Backend

Minimal FastAPI backend for the Airport Investment Agent.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive docs at `/docs`
and a health check at `/api/v1/health`.
