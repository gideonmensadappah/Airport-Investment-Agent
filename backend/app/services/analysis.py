from app.models.analysis import (
    AirportResult,
    AnalysisResponse,
    ComponentScores,
    SourceInfo,
)
from app.services.airport_data import AeroDataBoxClient, AirportRecord, AirportRepository
from app.services.scoring import (
    component_scores,
    congestion_score,
    expansion_opportunity_score,
)


METRICS_SOURCE = SourceInfo(
    name="Bundled MVP airport metrics",
    period="Illustrative MVP snapshot",
    scope=(
        "Demand growth, capacity-pressure and long-haul inputs; also used for delay "
        "and cancellation fallback when AeroDataBox is unavailable."
    ),
)

AERODATABOX_SOURCE = SourceInfo(
    name="AeroDataBox via RapidAPI",
    url="https://rapidapi.com/aedbx-aedbx/api/aerodatabox",
    period="Current two-hour delay window per airport",
    scope="Airport metadata, median departure delay and departure cancellations.",
)


class AnalysisService:
    def __init__(
        self,
        repository: AirportRepository,
        aerodatabox: AeroDataBoxClient,
        use_live_data: bool = True,
    ) -> None:
        self.repository = repository
        self.aerodatabox = aerodatabox
        self.use_live_data = use_live_data

    def compare_congestion(self, airport_codes: list[str]) -> AnalysisResponse:
        records = [self.repository.get(code) for code in airport_codes]
        records = self._enrich(records)
        results = sorted(
            [self._congestion_result(record) for record in records],
            key=lambda result: result.score,
            reverse=True,
        )
        leader = results[0]
        runner_up = results[1]
        gap = round(leader.score - runner_up.score, 1)
        return AnalysisResponse(
            tool="compare_congestion",
            title="Operational congestion comparison",
            summary=(
                f"{leader.code} has the stronger congestion signal at {leader.score}/100, "
                f"{gap} points above {runner_up.code}."
            ),
            results=results,
            confidence=self._confidence(records),
            assumptions=[
                "Congestion is represented by median departure delay (70%) and cancellation rate (30%).",
                "Delay is normalized to a 0-30 minute peer bound; cancellations to a 0-5% bound.",
            ],
            limitations=[
                "The score measures operational pressure, not terminal occupancy or design capacity.",
                self._fallback_limitation(records),
            ],
            sources=self._sources(records),
            methodology=(
                "Congestion Score = 70% normalized departure delay + 30% normalized "
                "cancellation rate. Missing inputs are omitted and remaining weights are renormalized."
            ),
        )

    def rank_expansion_candidates(self, region: str, limit: int = 5) -> AnalysisResponse:
        records = self._enrich(self.repository.for_region(region))
        results = sorted(
            [self._opportunity_result(record) for record in records],
            key=lambda result: result.score,
            reverse=True,
        )[:limit]
        leader = results[0]
        return AnalysisResponse(
            tool="rank_expansion_candidates",
            title=f"{region} expansion opportunity ranking",
            summary=(
                f"{leader.code} ranks first in the {region} MVP peer group with an "
                f"expansion opportunity score of {leader.score}/100."
            ),
            results=results,
            confidence=self._confidence(records),
            assumptions=[
                "All component scores use fixed MVP peer-reference bounds so results remain reproducible.",
                "Unavailable components are omitted and supported weights are proportionally renormalized.",
            ],
            limitations=[
                "The ranking is a screening signal, not a profitability forecast.",
                "Construction cost, land, financing, regulation and non-aeronautical revenue are out of scope.",
                self._fallback_limitation(records),
            ],
            sources=self._sources(records),
            methodology=(
                "Opportunity Score = 35% demand growth + 30% congestion + "
                "25% capacity pressure + 10% long-haul opportunity."
            ),
        )

    def _enrich(self, records: list[AirportRecord]) -> list[AirportRecord]:
        if not self.use_live_data:
            return records
        return self.aerodatabox.enrich_many(records)

    @staticmethod
    def _congestion_result(record: AirportRecord) -> AirportResult:
        score = congestion_score(record.metrics)
        if score is None:
            raise ValueError(f"No congestion inputs are available for {record.code}.")
        return AirportResult(
            code=record.code,
            name=record.name,
            city=record.city,
            state=record.state,
            region=record.region,
            score=score,
            score_label="congestion",
            metrics=record.metrics,
            component_scores=component_scores(record.metrics),
            metadata_source=record.metadata_source,
            operational_data_source=record.operational_data_source,
        )

    @staticmethod
    def _opportunity_result(record: AirportRecord) -> AirportResult:
        scored = expansion_opportunity_score(record.metrics)
        return AirportResult(
            code=record.code,
            name=record.name,
            city=record.city,
            state=record.state,
            region=record.region,
            score=scored.score,
            score_label="expansion_opportunity",
            metrics=record.metrics,
            component_scores=scored.components,
            metadata_source=record.metadata_source,
            operational_data_source=record.operational_data_source,
        )

    @staticmethod
    def _confidence(records: list[AirportRecord]) -> str:
        live_count = sum(record.operational_data_source == "aerodatabox" for record in records)
        if live_count == len(records):
            return "high"
        if live_count:
            return "medium"
        return "low"

    @staticmethod
    def _fallback_limitation(records: list[AirportRecord]) -> str:
        fallback_codes = [
            record.code
            for record in records
            if record.operational_data_source == "local_fallback"
        ]
        if not fallback_codes:
            return "AeroDataBox coverage and its two-hour observation window still limit comparability."
        return (
            "AeroDataBox operational data was unavailable for "
            f"{', '.join(fallback_codes)}; clearly labeled bundled fallback values were used."
        )

    @staticmethod
    def _sources(records: list[AirportRecord]) -> list[SourceInfo]:
        sources = [METRICS_SOURCE]
        if any(
            record.metadata_source == "aerodatabox"
            or record.operational_data_source == "aerodatabox"
            for record in records
        ):
            sources.insert(0, AERODATABOX_SOURCE)
        return sources
