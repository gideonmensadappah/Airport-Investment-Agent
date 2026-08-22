from dataclasses import dataclass

from app.models.analysis import AirportMetrics, ComponentScores


OPPORTUNITY_WEIGHTS = {
    "demand_growth": 0.35,
    "congestion": 0.30,
    "capacity_pressure": 0.25,
    "long_haul_opportunity": 0.10,
}


def _bounded_score(value: float | None, lower: float, upper: float) -> float | None:
    if value is None:
        return None
    clamped = max(lower, min(value, upper))
    return round((clamped - lower) / (upper - lower) * 100, 1)


def congestion_score(metrics: AirportMetrics) -> float | None:
    delay = _bounded_score(metrics.average_departure_delay_minutes, 0, 30)
    cancellations = _bounded_score(metrics.cancellation_rate_pct, 0, 5)
    available = [
        (delay, 0.70),
        (cancellations, 0.30),
    ]
    present = [(value, weight) for value, weight in available if value is not None]
    if not present:
        return None
    weight_sum = sum(weight for _, weight in present)
    return round(sum(value * weight for value, weight in present) / weight_sum, 1)


def component_scores(metrics: AirportMetrics) -> ComponentScores:
    return ComponentScores(
        demand_growth=_bounded_score(metrics.demand_growth_pct, -2, 12),
        congestion=congestion_score(metrics),
        capacity_pressure=_bounded_score(metrics.capacity_pressure_pct, 60, 95),
        long_haul_opportunity=_bounded_score(metrics.long_haul_share_pct, 0, 30),
    )


@dataclass(frozen=True)
class ScoreResult:
    score: float
    components: ComponentScores
    supported_weight: float


def expansion_opportunity_score(metrics: AirportMetrics) -> ScoreResult:
    components = component_scores(metrics)
    values = components.model_dump()
    present = [
        (values[name], weight)
        for name, weight in OPPORTUNITY_WEIGHTS.items()
        if values[name] is not None
    ]
    if not present:
        raise ValueError("Cannot calculate an opportunity score without supported metrics.")

    supported_weight = sum(weight for _, weight in present)
    score = sum(value * weight for value, weight in present) / supported_weight
    return ScoreResult(
        score=round(score, 1),
        components=components,
        supported_weight=round(supported_weight, 2),
    )
