import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.models.analysis import AirportMetrics


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "airport_metrics.json"


@dataclass(frozen=True)
class AirportRecord:
    code: str
    name: str
    city: str
    state: str
    region: str
    metrics: AirportMetrics
    metadata_source: str = "local_fallback"
    operational_data_source: str = "local_fallback"
    observation_period: str = "Illustrative MVP snapshot"


class UnknownAirportError(ValueError):
    pass


class AirportRepository:
    def __init__(self, data_file: Path = DATA_FILE) -> None:
        rows = json.loads(data_file.read_text(encoding="utf-8"))
        self._records = {
            row["code"]: AirportRecord(
                code=row["code"],
                name=row["name"],
                city=row["city"],
                state=row["state"],
                region=row["region"],
                metrics=AirportMetrics(**row),
            )
            for row in rows
        }

    @property
    def supported_codes(self) -> set[str]:
        return set(self._records)

    @property
    def supported_regions(self) -> set[str]:
        return {record.region for record in self._records.values()}

    def get(self, code: str) -> AirportRecord:
        normalized = code.strip().upper()
        try:
            return self._records[normalized]
        except KeyError as exc:
            raise UnknownAirportError(
                f"Airport {normalized!r} is not in the MVP dataset. "
                f"Supported codes: {', '.join(sorted(self._records))}."
            ) from exc

    def for_region(self, region: str) -> list[AirportRecord]:
        normalized = region.strip().casefold()
        records = [
            record
            for record in self._records.values()
            if record.region.casefold() == normalized
        ]
        if not records:
            raise ValueError(f"Region {region!r} is not supported by the MVP dataset.")
        return records


def _duration_to_minutes(value: str | None) -> float | None:
    if not value:
        return None
    match = re.fullmatch(
        r"(?P<sign>-?)(?P<hours>\d+):(?P<minutes>\d{2}):(?P<seconds>\d{2})",
        value,
    )
    if not match:
        return None
    minutes = (
        int(match.group("hours")) * 60
        + int(match.group("minutes"))
        + int(match.group("seconds")) / 60
    )
    return round(-minutes if match.group("sign") else minutes, 1)


class AeroDataBoxClient:
    """Fetches airport metadata and current delay statistics through RapidAPI."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        rapidapi_host: str,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.rapidapi_host = rapidapi_host
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def enrich_many(self, records: list[AirportRecord]) -> list[AirportRecord]:
        if not self.configured:
            return records
        with ThreadPoolExecutor(max_workers=min(6, len(records))) as executor:
            return list(executor.map(self.enrich, records))

    def enrich(self, record: AirportRecord) -> AirportRecord:
        metadata = self._safe_get(f"/airports/iata/{record.code}")
        delays = self._safe_get(f"/airports/iata/{record.code}/delays")

        enriched = record
        if metadata:
            enriched = replace(
                enriched,
                name=metadata.get("fullName") or metadata.get("shortName") or record.name,
                city=metadata.get("municipalityName") or record.city,
                metadata_source="aerodatabox",
            )

        if delays:
            departure = delays.get("departuresDelayInformation") or {}
            total = departure.get("numTotal")
            cancelled = departure.get("numCancelled")
            cancellation_rate = None
            if isinstance(total, int) and total > 0 and isinstance(cancelled, int):
                cancellation_rate = round(cancelled / total * 100, 1)

            median_delay = _duration_to_minutes(departure.get("medianDelay"))
            if median_delay is not None and cancellation_rate is not None:
                live_metrics = enriched.metrics.model_copy(
                    update={
                        "average_departure_delay_minutes": median_delay,
                        "cancellation_rate_pct": cancellation_rate,
                    }
                )
                enriched = replace(
                    enriched,
                    metrics=live_metrics,
                    operational_data_source="aerodatabox",
                    observation_period=_format_period(
                        delays.get("from"),
                        delays.get("to"),
                    ),
                )

        return enriched

    def _safe_get(self, path: str) -> dict:
        try:
            return self._get(path)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
            return {}

    def _get(self, path: str) -> dict:
        if not self.api_key:
            raise RuntimeError("AeroDataBox API key is not configured")
        request = Request(
            f"{self.base_url}{path}",
            headers={
                "Accept": "application/json",
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.rapidapi_host,
                "User-Agent": "AirIntel-MVP/0.1",
            },
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status == 204:
                return {}
            payload = json.load(response)
        return payload if isinstance(payload, dict) else {}


def _format_period(start: dict | None, end: dict | None) -> str:
    start_value = (start or {}).get("local") or (start or {}).get("utc")
    end_value = (end or {}).get("local") or (end or {}).get("utc")
    if start_value and end_value:
        return f"{start_value} to {end_value}"
    return "Current AeroDataBox two-hour delay window"
