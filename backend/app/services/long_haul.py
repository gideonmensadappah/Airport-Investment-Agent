import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from app.models.analysis import (
    LongHaulAnalysisResponse,
    LongHaulRoute,
    SourceInfo,
)
from app.services.airport_data import AeroDataBoxClient


SNAPSHOT_FILE = Path(__file__).resolve().parents[1] / "data" / "long_haul_snapshot.json"
EARTH_RADIUS_MILES = 3958.7613


def great_circle_miles(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
) -> float:
    """Calculate great-circle distance with the Haversine formula."""
    lat1, lon1, lat2, lon2 = map(
        math.radians,
        (origin_lat, origin_lon, destination_lat, destination_lon),
    )
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return EARTH_RADIUS_MILES * 2 * math.asin(math.sqrt(haversine))


class LongHaulService:
    def __init__(
        self,
        aerodatabox: AeroDataBoxClient,
        threshold_miles: float = 3000.0,
        snapshot_file: Path = SNAPSHOT_FILE,
        use_live_data: bool = True,
    ) -> None:
        if threshold_miles <= 0:
            raise ValueError("Long-haul threshold must be greater than zero.")
        self.aerodatabox = aerodatabox
        self.threshold_miles = threshold_miles
        self.use_live_data = use_live_data
        payload = json.loads(snapshot_file.read_text(encoding="utf-8"))
        self._snapshots = {row["airport"]: row for row in payload["airports"]}

    def analyze_long_haul_share(self, airport: str) -> LongHaulAnalysisResponse:
        code = airport.strip().upper()
        snapshot = self._snapshots.get(code)

        if self.use_live_data and self.aerodatabox.configured:
            origin = self._origin_metadata(code, snapshot)
            route_payload = self.aerodatabox.get_daily_routes(code)
            routes = route_payload.get("routes") if route_payload else None
            if origin and isinstance(routes, list) and routes:
                return self._from_live_routes(code, origin, routes)

        if snapshot and math.isclose(
            float(snapshot["threshold_miles"]), self.threshold_miles
        ):
            return self._from_snapshot(snapshot)

        raise ValueError(
            f"Long-haul route data is unavailable for {code}. "
            "The bundled MVP snapshot currently supports ANC."
        )

    def _origin_metadata(self, code: str, snapshot: dict | None) -> dict:
        if snapshot:
            return {
                "name": snapshot["airport_name"],
                "location": snapshot["origin_location"],
                "timeZone": snapshot.get("time_zone"),
            }
        metadata = self.aerodatabox.get_airport_metadata(code)
        return {
            "name": metadata.get("fullName") or metadata.get("shortName") or code,
            "location": metadata.get("location"),
            "timeZone": metadata.get("timeZone"),
        }

    def _from_live_routes(
        self,
        code: str,
        origin: dict,
        rows: list[dict],
    ) -> LongHaulAnalysisResponse:
        origin_location = origin.get("location") or {}
        origin_lat = _number(origin_location.get("lat"))
        origin_lon = _number(origin_location.get("lon"))
        if origin_lat is None or origin_lon is None:
            raise ValueError(f"Airport coordinates are unavailable for {code}.")

        total = 0.0
        known = 0.0
        long_haul_total = 0.0
        long_haul_routes: list[LongHaulRoute] = []
        for row in rows:
            average = _number(row.get("averageDailyFlights"))
            if average is None or average < 0:
                continue
            total += average
            destination = row.get("destination") or {}
            location = destination.get("location") or {}
            lat = _number(location.get("lat"))
            lon = _number(location.get("lon"))
            if lat is None or lon is None:
                continue
            distance = great_circle_miles(origin_lat, origin_lon, lat, lon)
            known += average
            if distance >= self.threshold_miles:
                long_haul_total += average
                long_haul_routes.append(
                    LongHaulRoute(
                        destination=destination.get("iata") or "N/A",
                        name=(
                            destination.get("shortName")
                            or destination.get("fullName")
                            or destination.get("iata")
                            or "Unknown airport"
                        ),
                        distance_miles=round(distance),
                        average_daily_flights=round(average, 2),
                    )
                )

        if known <= 0:
            raise ValueError(f"No routes with known destination distance for {code}.")

        period = _live_period(origin.get("timeZone"))
        long_haul_routes.sort(
            key=lambda route: route.average_daily_flights,
            reverse=True,
        )
        return self._build_response(
            code=code,
            airport_name=origin.get("name") or code,
            total=total,
            known=known,
            long_haul_total=long_haul_total,
            routes=long_haul_routes[:8],
            period=period,
            source_name="AeroDataBox daily route statistics via RapidAPI",
            source_scope="Live route-level average daily departure frequencies",
            fallback_note=None,
        )

    def _from_snapshot(self, snapshot: dict) -> LongHaulAnalysisResponse:
        retrieved_at = snapshot["retrieved_at_utc"]
        return self._build_response(
            code=snapshot["airport"],
            airport_name=snapshot["airport_name"],
            total=float(snapshot["total_average_daily_flights"]),
            known=float(snapshot["known_distance_average_daily_flights"]),
            long_haul_total=float(snapshot["long_haul_average_daily_flights"]),
            routes=[LongHaulRoute(**row) for row in snapshot["top_long_haul_routes"]],
            period=snapshot["observation_period"],
            source_name="Bundled AeroDataBox long-haul snapshot",
            source_scope=f"Snapshot retrieved at {retrieved_at}",
            fallback_note=(
                "The live API was unavailable or disabled, so this result uses the "
                f"bundled snapshot retrieved at {retrieved_at}."
            ),
        )

    def _build_response(
        self,
        *,
        code: str,
        airport_name: str,
        total: float,
        known: float,
        long_haul_total: float,
        routes: list[LongHaulRoute],
        period: str,
        source_name: str,
        source_scope: str,
        fallback_note: str | None,
    ) -> LongHaulAnalysisResponse:
        share = round(long_haul_total / known * 100, 1)
        coverage = round(known / total * 100, 1) if total > 0 else 0.0
        limitations = [
            "Great-circle distance is a route-screening proxy, not actual flown distance.",
            "Daily route statistics may include cargo or other scheduled operations; they are not passenger-only counts.",
        ]
        if fallback_note:
            limitations.append(fallback_note)
        confidence = "high" if coverage >= 95 and fallback_note is None else "medium"
        return LongHaulAnalysisResponse(
            title=f"Long-haul share from {code}",
            summary=(
                f"{code}'s long-haul share is {share:.1f}%: "
                f"{long_haul_total:.2f} of {known:.2f} average daily departures "
                f"with known destination distance travel at least "
                f"{self.threshold_miles:,.0f} miles."
            ),
            origin=code,
            airport_name=airport_name,
            threshold_miles=self.threshold_miles,
            long_haul_share_pct=share,
            long_haul_average_daily_flights=round(long_haul_total, 2),
            known_distance_average_daily_flights=round(known, 2),
            total_average_daily_flights=round(total, 2),
            coverage_pct=coverage,
            observation_period=period,
            results=routes,
            confidence=confidence,
            assumptions=[
                f"Long-haul means at least {self.threshold_miles:,.0f} statute miles great-circle distance.",
                "The percentage is weighted by average daily departure frequency, not by destination count.",
            ],
            limitations=limitations,
            sources=[
                SourceInfo(
                    name=source_name,
                    url="https://doc.aerodatabox.com/",
                    period=period,
                    scope=source_scope,
                )
            ],
            methodology=(
                "For each destination, compute Haversine great-circle distance "
                "from the origin. Sum average daily departures for routes at or "
                f"above {self.threshold_miles:,.0f} miles, then divide by average "
                "daily departures for all routes with known coordinates."
            ),
        )


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _live_period(time_zone: str | None) -> str:
    try:
        local_date = datetime.now(timezone.utc).astimezone(ZoneInfo(time_zone)).date()
    except (KeyError, TypeError, ValueError):
        local_date = datetime.now(timezone.utc).date()
    return f"Trailing seven local days before {local_date.isoformat()}"
