# Airport Investment Intelligence Agent

## Prerequisites

- Python 3.12
- Node.js 24

## Architecture

The production-shaped demo is deployed as two independently built services:

- A React/Vite static site served from Render's CDN.
- A Dockerized FastAPI web service on Render's free web-service tier.

The API uses `data/airport_data.db` as an immutable SQLite read model. The
snapshot is generated offline from the public US DOT DB1C Market dataset and
is included in the runtime image; the 5+ GB raw source file is never copied
into the image. Live AeroDataBox enrichment is optional and falls back to the
bundled metrics when no API key is configured.


## Run the Stage 1 flow

The frontend and backend are separate development servers. Keep both terminals open.

### Terminal 1 - API

```powershell
cd backend

# Create the virtual environment (once)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend and data-pipeline dependencies
python -m pip install -r requirements-dev.txt

# Check dependency compatibility (optional)
python -m pip check

# Run backend unit tests (optional)
python -m unittest discover -s tests -v

# Start the backend server
python -m uvicorn app.main:app --reload --port 8000

```

Verify the API at `http://127.0.0.1:8000/api/v1/health`.

### Terminal 2 - client

```powershell
cd frontend

# Install locked frontend dependencies
npm ci

# Start the frontend development server
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to the API on port 8000.

Stage 1 supports examples such as:

```text
Compare LAX and Santa Ana airport congestion.
Compare SFO and LAX congestion.
```

## Tests

```powershell
cd backend
python -m unittest discover -s tests -v
```

```powershell
cd frontend
npm run build
```

## Build the local aviation database

The raw public dataset remains the source of truth. Build the local SQLite read
model from the repository root:

```powershell
python backend/scripts/build_airport_database.py
```

For a faster, airport-specific build during development:

```powershell
python backend/scripts/build_airport_database.py --airports SFO LAX
```

Demand is aggregated by origin, destination, nonstop status, and market-coupon
count. The database also retains passenger-weighted itinerary distance,
distance bounds, dataset provenance, and import statistics. The raw input is
ignored by Git; the generated, aggregated snapshot is tracked because it is the
versioned runtime artifact used by deployments.

## Run the deployment image locally

```powershell
docker build -t airport-investment-agent-api .
docker run --rm -p 8000:10000 `
  -e CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173 `
  airport-investment-agent-api
```

Verify `http://127.0.0.1:8000/api/v1/health`.

## Deploy to Render for free

1. Push the repository, including `data/airport_data.db`, to GitHub, GitLab, or
   Bitbucket.
2. In Render, choose **New > Blueprint** and connect the repository.
3. Render reads `render.yaml` and creates:
   - `airport-investment-agent-web`, a free static site.
   - `airport-investment-agent-api`, a free Docker web service.
4. Optionally add `AERODATABOX_API_KEY` to the API service as a secret
   environment variable. Without it, the bundled fallback data remains usable.

The Blueprint passes each service's generated public URL to the other service:
the frontend receives `VITE_API_BASE_URL`, and the API receives the exact CORS
origin. No deployment URL is hard-coded.

Render's free API service sleeps after periods of inactivity. The static UI
remains available and explains that the first analysis can take up to a minute
while the API wakes.
