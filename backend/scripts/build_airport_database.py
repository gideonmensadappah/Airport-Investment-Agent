"""Build the application's SQLite read model from public aviation datasets."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("data/raw/DB1C.MARKET.202604.15JUL2026.csv")
DEFAULT_METRICS = Path("backend/app/data/airport_metrics.json")
DEFAULT_OUTPUT = Path("data/airport_data.db")
REQUIRED_COLUMNS = [
    "Origin",
    "Dest",
    "Passengers",
    "Nonstop",
    "MktCoupons",
    "TotalDistance",
    "NonStopMiles",
]

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE airports (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    state TEXT,
    region TEXT
);

CREATE TABLE airport_metrics (
    airport_code TEXT NOT NULL REFERENCES airports(code),
    observation_period TEXT NOT NULL,
    average_departure_delay_minutes REAL,
    cancellation_rate_pct REAL,
    demand_growth_pct REAL,
    capacity_pressure_pct REAL,
    long_haul_share_pct REAL,
    source TEXT NOT NULL,
    PRIMARY KEY (airport_code, observation_period)
);

CREATE TABLE market_demand (
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    nonstop INTEGER NOT NULL CHECK (nonstop IN (0, 1)),
    market_coupons INTEGER NOT NULL CHECK (market_coupons >= 1),
    passengers REAL NOT NULL CHECK (passengers >= 0),
    weighted_total_distance REAL NOT NULL,
    min_total_distance REAL,
    max_total_distance REAL,
    nonstop_miles REAL,
    PRIMARY KEY (origin, destination, nonstop, market_coupons)
);

CREATE TABLE dataset_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

UPSERT_DEMAND = """
INSERT INTO market_demand (
    origin, destination, nonstop, market_coupons, passengers,
    weighted_total_distance, min_total_distance, max_total_distance, nonstop_miles
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(origin, destination, nonstop, market_coupons) DO UPDATE SET
    passengers = passengers + excluded.passengers,
    weighted_total_distance = weighted_total_distance + excluded.weighted_total_distance,
    min_total_distance = MIN(min_total_distance, excluded.min_total_distance),
    max_total_distance = MAX(max_total_distance, excluded.max_total_distance),
    nonstop_miles = COALESCE(nonstop_miles, excluded.nonstop_miles)
"""


def _normalize_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    input_rows = len(chunk)
    for column in ("Origin", "Dest"):
        chunk[column] = chunk[column].astype("string").str.strip().str.upper()
    for column in ("Passengers", "Nonstop", "MktCoupons", "TotalDistance", "NonStopMiles"):
        chunk[column] = pd.to_numeric(chunk[column], errors="coerce")

    valid = (
        chunk["Origin"].str.fullmatch(r"[A-Z]{3}", na=False)
        & chunk["Dest"].str.fullmatch(r"[A-Z]{3}", na=False)
        & chunk["Passengers"].notna()
        & chunk["Passengers"].ge(0)
        & chunk["Nonstop"].isin([0, 1])
        & chunk["MktCoupons"].notna()
        & chunk["MktCoupons"].ge(1)
        & chunk["TotalDistance"].notna()
        & chunk["TotalDistance"].ge(0)
    )
    clean = chunk.loc[valid].copy()
    clean["Nonstop"] = clean["Nonstop"].astype(int)
    clean["MktCoupons"] = clean["MktCoupons"].astype(int)
    clean["weighted_total_distance"] = clean["Passengers"] * clean["TotalDistance"]
    return clean, input_rows - len(clean)


def _aggregate_chunk(chunk: pd.DataFrame) -> list[tuple]:
    grouped = (
        chunk.groupby(["Origin", "Dest", "Nonstop", "MktCoupons"], as_index=False)
        .agg(
            passengers=("Passengers", "sum"),
            weighted_total_distance=("weighted_total_distance", "sum"),
            min_total_distance=("TotalDistance", "min"),
            max_total_distance=("TotalDistance", "max"),
            nonstop_miles=("NonStopMiles", "max"),
        )
    )
    grouped = grouped.where(pd.notna(grouped), None)
    return list(grouped.itertuples(index=False, name=None))


def _load_airport_metrics(connection: sqlite3.Connection, metrics_file: Path) -> None:
    rows = json.loads(metrics_file.read_text(encoding="utf-8"))
    connection.executemany(
        "INSERT INTO airports (code, name, city, state, region) VALUES (?, ?, ?, ?, ?)",
        [(row["code"], row["name"], row.get("city"), row.get("state"), row.get("region")) for row in rows],
    )
    connection.executemany(
        """INSERT INTO airport_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                row["code"], "Illustrative MVP snapshot",
                row.get("average_departure_delay_minutes"), row.get("cancellation_rate_pct"),
                row.get("demand_growth_pct"), row.get("capacity_pressure_pct"),
                row.get("long_haul_share_pct"), "Bundled MVP airport metrics",
            )
            for row in rows
        ],
    )


def build_database(
    input_file: Path,
    output_file: Path,
    metrics_file: Path = DEFAULT_METRICS,
    chunk_size: int = 250_000,
    airports: set[str] | None = None,
) -> dict[str, int | float]:
    """Build a new database atomically and return import statistics."""
    input_file = input_file.resolve()
    output_file = output_file.resolve()
    metrics_file = metrics_file.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = output_file.with_suffix(output_file.suffix + ".tmp")
    if temporary_file.exists():
        temporary_file.unlink()

    normalized_airports = {code.strip().upper() for code in airports} if airports else None
    stats: dict[str, int | float] = {"rows_read": 0, "rows_rejected": 0, "passengers": 0.0}

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(temporary_file)
        with connection:
            connection.executescript(SCHEMA)
            _load_airport_metrics(connection, metrics_file)

            for chunk in pd.read_csv(input_file, usecols=REQUIRED_COLUMNS, chunksize=chunk_size):
                stats["rows_read"] += len(chunk)
                clean, rejected = _normalize_chunk(chunk)
                stats["rows_rejected"] += rejected
                if normalized_airports is not None:
                    clean = clean[clean["Origin"].isin(normalized_airports)]
                if clean.empty:
                    continue
                stats["passengers"] += float(clean["Passengers"].sum())
                connection.executemany(UPSERT_DEMAND, _aggregate_chunk(clean))

            metadata = {
                "schema_version": "1",
                "status": "complete",
                "source_file": input_file.name,
                "source_size_bytes": str(input_file.stat().st_size),
                "imported_at_utc": datetime.now(timezone.utc).isoformat(),
                "rows_read": str(stats["rows_read"]),
                "rows_rejected": str(stats["rows_rejected"]),
                "passengers": str(stats["passengers"]),
                "origin_filter": ",".join(sorted(normalized_airports or [])) or "all",
            }
            connection.executemany("INSERT INTO dataset_metadata VALUES (?, ?)", metadata.items())
            connection.executescript(
                """
                CREATE INDEX idx_market_demand_origin_destination
                    ON market_demand(origin, destination);
                CREATE INDEX idx_market_demand_origin_nonstop
                    ON market_demand(origin, nonstop);
                """
            )
            invalid = connection.execute(
                "SELECT COUNT(*) FROM market_demand WHERE passengers < 0 OR nonstop NOT IN (0, 1)"
            ).fetchone()[0]
            if invalid:
                raise ValueError(f"Database validation found {invalid} invalid demand rows")

        connection.close()
        connection = None
        os.replace(temporary_file, output_file)
        return stats
    except BaseException:
        if connection is not None:
            connection.close()
        temporary_file.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    parser.add_argument("--airports", nargs="*", help="Optional origin IATA codes")
    args = parser.parse_args()
    stats = build_database(
        args.input, args.output, args.metrics, args.chunk_size,
        set(args.airports) if args.airports else None,
    )
    print(f"Built {args.output}: {stats}")


if __name__ == "__main__":
    main()
