# Airport Investment Intelligence Agent

[![CI](https://github.com/gideonmensadappah/Airport-Investment-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/gideonmensadappah/Airport-Investment-Agent/actions/workflows/ci.yml)

A conversational airport-investment screening demo. An LLM selects a typed
analysis tool, deterministic services calculate the result, and the interface
shows the source, period, assumptions, limitations, and confidence alongside
the answer.

## Demo

- [Live application](https://airport-investment-agent-web.onrender.com/)
- [27-second product walkthrough](https://youtu.be/_YkvdFmvZgU)
- [Design and architecture document](docs/HLD.md)

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

Long-haul analysis uses AeroDataBox daily route statistics, which summarize the
trailing seven local days. It calculates great-circle distance for each
destination and weights the result by average daily departure frequency. A
versioned ANC snapshot keeps the assignment's Anchorage example reproducible
when the optional API is unavailable.

OpenAI's Responses API provides the conversational orchestration layer. The
model selects one of the typed analysis tools and explains its structured
output; all metrics and scores remain deterministic. When no OpenAI key is
configured, the API falls back to the original rule-based intent router.


## Run the complete demo locally

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

To enable LLM orchestration locally, copy `backend/.env.example` to
`backend/.env` and set `OPENAI_API_KEY`. Keep this server-side file out of Git;
never expose the key through a `VITE_` frontend variable.

### Terminal 2 - client

```powershell
cd frontend

# Install locked frontend dependencies
npm ci

# Start the frontend development server
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` requests to the API on port 8000.

Recommended reviewer prompts:

```text
Compare LAX and Santa Ana airport congestion.
Rank New England airports for expansion opportunity.
Show unmet demand from LAX.
What is the percentage of long-haul flights out of Anchorage airport?
```

| Workflow | Deterministic result | Primary data |
| --- | --- | --- |
| Congestion comparison | Fixed normalization of departure delay and cancellation rate | AeroDataBox when configured; labeled bundled metrics otherwise |
| Regional expansion ranking | Weighted demand, congestion, capacity-pressure, and long-haul components | Bundled reproducible MVP inputs with optional live operational enrichment |
| Unmet-demand screening | Connecting-passenger volume and share proxy | Public US DOT DB1C Market snapshot |
| Long-haul share | Average daily departures on routes of at least 3,000 great-circle miles divided by departures with known destination distance | AeroDataBox trailing-seven-day route statistics; versioned ANC fallback |

The bundled fallbacks are deliberate demo artifacts, not silently presented as
live data. Every response labels its source and observation period.

## Tests

```powershell
cd backend
python -m unittest discover -s tests -v
```

```powershell
cd frontend
npm run build
```

GitHub Actions repeats both checks and builds the production Docker image on
every push and pull request. Render deploys only after those checks pass.

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
4. Add `OPENAI_API_KEY` to enable LLM tool selection and conversational
   explanations. Without it, deterministic routing remains available.
5. Optionally add `AERODATABOX_API_KEY` for live airport and route data.
   Without it, the labeled bundled fallbacks remain usable.

Both keys are declared with `sync: false` and are never stored in Git. Render
prompts for them during initial Blueprint creation. If the Blueprint already
exists, add newly introduced secrets manually in the API service dashboard.

The Blueprint passes each service's generated public URL to the other service:
the frontend receives `VITE_API_BASE_URL`, and the API receives the exact CORS
origin. No deployment URL is hard-coded.

Render's free API service sleeps after periods of inactivity. The static UI
remains available and explains that the first analysis can take up to a minute
while the API wakes.

## Submission readiness checklist

- `python -m unittest discover -s tests -v` passes from `backend/`.
- `npm run build` passes from `frontend/`.
- The Docker image builds from the repository root.
- `/api/v1/health` returns `{"status":"ok","data":"ready"}`.
- `OPENAI_API_KEY` and, optionally, `AERODATABOX_API_KEY` are configured only
  as server-side secrets.
- The four reviewer prompts above return structured results with visible
  methodology, source period, assumptions, and limitations.
