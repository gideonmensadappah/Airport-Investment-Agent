# Airport Investment Intelligence Agent

## Prerequisites

- Python 3.12
- Node.js 24


## Run the Stage 1 flow

The frontend and backend are separate development servers. Keep both terminals open.

### Terminal 1 - API

```powershell
cd backend

# Create the virtual environment (once)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
python -m pip install -r requirements.txt

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
python scripts/build_airport_database.py
```

For a faster, airport-specific build during development:

```powershell
python scripts/build_airport_database.py --airports SFO LAX
```

The generated `data/airport_data.db` is intentionally ignored by Git. Demand is
aggregated by origin, destination, nonstop status, and market-coupon count. The
database also retains passenger-weighted itinerary distance, distance bounds,
dataset provenance, and import statistics.
