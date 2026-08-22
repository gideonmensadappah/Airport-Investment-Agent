import pandas as pd
from pathlib import Path

AIRPORT = "LAX"
CHUNK_SIZE = 250_000

INPUT_FILE = Path("data/raw/DB1C.MARKET.202604.15JUL2026.csv")
OUTPUT_FILE = Path(f"data/processed/{AIRPORT.lower()}_demand.csv")

COLUMNS = [
    "Origin",
    "Dest",
    "Passengers",
    "Nonstop",
    "MktCoupons",
    "AirportGroup",
    "TotalDistance",
    "NonStopMiles",
]


def build_demand_dataset():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    airport_chunks = []

    for chunk in pd.read_csv(
        INPUT_FILE,
        usecols=COLUMNS,
        chunksize=CHUNK_SIZE,
    ):
        filtered = chunk[chunk["Origin"] == AIRPORT]

        if not filtered.empty:
            airport_chunks.append(filtered)

    result = pd.concat(airport_chunks, ignore_index=True)

    result.to_csv(OUTPUT_FILE, index=False)

    print(f"Airport: {AIRPORT}")
    print(f"Rows: {len(result):,}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_demand_dataset()