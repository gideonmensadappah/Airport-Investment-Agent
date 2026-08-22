from app.models.tool_calls import (
    AnalyzeUnmetDemandArguments,
    AnalyzeUnmetDemandToolCall,
    ClarificationDecision,
    CompareCongestionArguments,
    CompareCongestionToolCall,
    RankExpansionCandidatesArguments,
    RankExpansionCandidatesToolCall,
    RoutingDecision,
)
from app.services.airport_resolver import AirportResolver


DEMAND_SIGNALS = (
    "unmet demand",
    "route opportunity",
    "route opportunities",
    "nonstop opportunity",
    "nonstop opportunities",
    "potential nonstop",
    "connecting demand",
    "passengers connect",
)

RANKING_SIGNALS = (
    "rank",
    "ranking",
    "expansion candidates",
    "best airports",
)

CONGESTION_SIGNALS = (
    "congestion",
    "delay",
    "delays",
    "cancellation",
    "operational pressure",
)


class IntentRouter:
    """Deterministic fallback router for typed airport-analysis tools."""

    def __init__(self, resolver: AirportResolver) -> None:
        self.resolver = resolver

    def route(self, message: str) -> RoutingDecision:
        normalized = " ".join(message.casefold().split())
        airports = self.resolver.extract_airports(message)

        if _contains_any(normalized, RANKING_SIGNALS):
            region = self.resolver.extract_region(message)
            if region is None:
                return ClarificationDecision(
                    message="Specify a supported region, for example New England.",
                )
            return RankExpansionCandidatesToolCall(
                arguments=RankExpansionCandidatesArguments(region=region),
            )

        if _contains_any(normalized, DEMAND_SIGNALS):
            if not airports:
                return ClarificationDecision(
                    message="Specify one origin airport, for example LAX.",
                )
            return AnalyzeUnmetDemandToolCall(
                arguments=AnalyzeUnmetDemandArguments(airport=airports[0]),
            )

        if _contains_any(normalized, CONGESTION_SIGNALS) or len(airports) >= 2:
            if len(airports) < 2:
                return ClarificationDecision(
                    message=(
                        "Congestion comparison requires at least two airports. "
                        "Try: Compare LAX and SFO congestion."
                    ),
                )
            return CompareCongestionToolCall(
                arguments=CompareCongestionArguments(airports=airports[:6]),
            )

        if airports:
            return ClarificationDecision(
                message=(
                    "Specify the analysis you want: congestion comparison or "
                    "potential nonstop opportunities."
                ),
            )

        return ClarificationDecision(
            message=(
                "Ask for an airport congestion comparison or potential nonstop "
                "opportunities, and include the relevant airport codes."
            ),
        )


def _contains_any(message: str, signals: tuple[str, ...]) -> bool:
    return any(signal in message for signal in signals)
