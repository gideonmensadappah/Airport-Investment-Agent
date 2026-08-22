from pathlib import Path

from db.database import DATABASE_FILE, get_connection
from app.models.analysis import (DemandOpportunity, DemandAnalysisResponse, SourceInfo)


CONNECTING_PASSENGER_REFERENCE = 3_000


# The unmet demand score is calculated as a weighted average of two components:
# 1. Connecting-passenger volume, normalized to a maximum of 100 at the reference bound.
# 2. Connecting share, expressed as a percentage of total passengers.
# The weights are 70% for volume and 30% for share, reflecting the relative importance of each factor in assessing unmet demand.
# The score is rounded to one decimal place for clarity and consistency in reporting.
def calculate_unmet_demand_score(
    connecting_passengers: float,
    connecting_share: float,
) -> float:
    volume_score = min(
        connecting_passengers / CONNECTING_PASSENGER_REFERENCE,
        1,
    ) * 100
    share_score = connecting_share * 100
    return round(0.70 * volume_score + 0.30 * share_score, 1)


class DemandService:
    def __init__(self, database_file: Path = DATABASE_FILE) -> None:
        self.database_file = database_file

    def get_unmet_demand(
        self,
        airport: str,
        top_n: int = 10,
        min_passengers: float = 0
    ) -> list[DemandOpportunity]:

        airport = airport.strip().upper()
        if len(airport) != 3 or not airport.isalpha():
            raise ValueError("airport must be a three-letter IATA code")

        if top_n < 1:
            raise ValueError("top_n must be positive")

        if not self.database_file.exists():
            raise FileNotFoundError(f"Airport database not found: {self.database_file}")

        query = """
            SELECT
                destination,
                SUM(passengers) AS total_passengers,
                SUM(CASE WHEN nonstop = 1 THEN passengers ELSE 0 END) AS nonstop_passengers,
                SUM(CASE WHEN nonstop = 0 THEN passengers ELSE 0 END) AS connecting_passengers,
                SUM(CASE WHEN nonstop = 0 THEN passengers * (market_coupons - 1) ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN nonstop = 0 THEN passengers ELSE 0 END), 0)
                    AS average_connections,
                SUM(weighted_total_distance) / NULLIF(SUM(passengers), 0)
                    AS average_itinerary_distance
            FROM market_demand
            WHERE origin = ?
            GROUP BY destination
            HAVING SUM(passengers) >= ?
            ORDER BY connecting_passengers DESC,
                    connecting_passengers / NULLIF(total_passengers, 0) DESC
        """

        connection = get_connection(self.database_file)

        try:
            rows = connection.execute(query, (airport, min_passengers)).fetchall()
        finally:
            connection.close()

        results: list[DemandOpportunity] = []
        for row in rows:
            result = dict(row)
            total = result["total_passengers"]
            # Note:
            # מחלק את הטיסות קונקשיין במספר הנוסעים הכולל.
            # כדי לקבל את החלק היחסי של הנוסעים שמבצעים קונקשיין
            connecting_share = (
                result["connecting_passengers"] / total if total else 0.0
            )
            results.append(
                DemandOpportunity(
                    destination=result["destination"],
                    total_passengers=result["total_passengers"],
                    nonstop_passengers=result["nonstop_passengers"],
                    connecting_passengers=result["connecting_passengers"],
                    connecting_share=connecting_share,
                    average_connections=result["average_connections"],
                    average_itinerary_distance=(
                        result["average_itinerary_distance"]
                    ),
                    score=calculate_unmet_demand_score(
                        result["connecting_passengers"],
                        connecting_share,
                    ),
                )
        )
        results.sort(key=lambda opportunity: opportunity.score, reverse=True)

        return results[:top_n]


    def analyze_unmet_demand(self, airport: str, top_n:int = 5, min_passengers: float = 100) -> DemandAnalysisResponse:
        airport = airport.strip().upper()

        results = self.get_unmet_demand(
            airport=airport,
            top_n=top_n,
            min_passengers=min_passengers
        )

        if not results:
            raise ValueError(f"No demand data is available for airport {airport}.")

        leader = results[0]

        summary = (
            f"{airport} shows its strongest unmet-demand signal to "
            f"{leader.destination}. "
            f"{leader.connecting_passengers:,.0f} of "
            f"{leader.total_passengers:,.0f} analyzed passengers traveled "
            f"without nonstop service "
            f"({leader.connecting_share:.1%} connecting share)."
        )

        return DemandAnalysisResponse(
            title=f"Potential route opportunities from {airport}",
            summary=summary,
            origin=airport,
            results=results,
            confidence="medium",
            assumptions=[
            (
                "Passengers using connecting itineraries are treated as "
                "a proxy for potential nonstop demand."
            ),
            (
                "A connecting-passenger volume of 3,000 receives the "
                "maximum volume component score."
            ),
        ],
        limitations=[
            (
                "Connecting traffic does not prove that passengers would "
                "purchase a new nonstop service."
            ),
            (
                "The analysis excludes fares, seasonality, aircraft economics, "
                "competition and operating costs."
            ),
            (
                "Some source rows contain inconsistencies between nonstop "
                "status and market-coupon count."
            ),
        ],
        sources=[
            SourceInfo(
                name="US DOT DB1C Market dataset",
                period="Bundled public-data snapshot",
                scope=(
                    "Passenger demand, nonstop status, itinerary distance "
                    "and market-coupon count."
                ),
            )
        ],
        methodology=(
            "Unmet Demand Score = 70% normalized connecting-passenger "
            "volume + 30% connecting share. Connecting volume is capped "
            "at the 3,000-passenger reference bound."
        ),
        )
