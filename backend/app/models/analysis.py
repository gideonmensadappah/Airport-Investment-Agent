from typing import Literal

from pydantic import BaseModel, Field


class AirportMetrics(BaseModel):
    average_departure_delay_minutes: float | None = None
    cancellation_rate_pct: float | None = None
    demand_growth_pct: float | None = None
    capacity_pressure_pct: float | None = None
    long_haul_share_pct: float | None = None


class ComponentScores(BaseModel):
    demand_growth: float | None = None
    congestion: float | None = None
    capacity_pressure: float | None = None
    long_haul_opportunity: float | None = None


class AirportResult(BaseModel):
    code: str
    name: str
    city: str
    state: str
    region: str
    score: float
    score_label: Literal["congestion", "expansion_opportunity"]
    metrics: AirportMetrics
    component_scores: ComponentScores
    metadata_source: Literal["aerodatabox", "local_fallback"]
    operational_data_source: Literal["aerodatabox", "local_fallback"]

class DemandOpportunity(BaseModel):
    destination: str
    total_passengers: float
    nonstop_passengers: float
    connecting_passengers: float
    connecting_share: float = Field(ge=0, le=1)
    average_connections: float | None = None
    average_itinerary_distance: float | None = None
    score: float = Field(ge=0, le=100)

class SourceInfo(BaseModel):
    name: str
    url: str | None = None
    period: str
    scope: str


class LongHaulRoute(BaseModel):
    destination: str
    name: str
    distance_miles: float = Field(ge=0)
    average_daily_flights: float = Field(ge=0)


class LongHaulAnalysisResponse(BaseModel):
    tool: Literal["analyze_long_haul_share"] = "analyze_long_haul_share"
    title: str
    summary: str
    origin: str
    airport_name: str
    threshold_miles: float = Field(gt=0)
    long_haul_share_pct: float = Field(ge=0, le=100)
    long_haul_average_daily_flights: float = Field(ge=0)
    known_distance_average_daily_flights: float = Field(ge=0)
    total_average_daily_flights: float = Field(ge=0)
    coverage_pct: float = Field(ge=0, le=100)
    observation_period: str
    results: list[LongHaulRoute]
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str]
    limitations: list[str]
    sources: list[SourceInfo]
    methodology: str

class DemandAnalysisResponse(BaseModel):
    tool: Literal["analyze_unmet_demand"] = "analyze_unmet_demand"
    title: str
    summary: str
    origin: str
    results: list[DemandOpportunity]
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str]
    limitations: list[str]
    sources: list[SourceInfo]
    methodology: str

class AnalysisResponse(BaseModel):
    tool: Literal["compare_congestion", "rank_expansion_candidates"]
    title: str
    summary: str
    results: list[AirportResult]
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str]
    limitations: list[str]
    sources: list[SourceInfo]
    methodology: str


class CompareRequest(BaseModel):
    airports: list[str] = Field(min_length=2, max_length=6)


class RankRequest(BaseModel):
    region: str = "New England"
    limit: int = Field(default=5, ge=1, le=10)


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=1000)
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    tool: Literal[
        "compare_congestion",
        "rank_expansion_candidates",
        "analyze_unmet_demand",
        "analyze_long_haul_share",
    ]
    title: str
    summary: str
    results: list[AirportResult] | list[DemandOpportunity] | list[LongHaulRoute]
    confidence: Literal["low", "medium", "high"]
    assumptions: list[str]
    limitations: list[str]
    sources: list[SourceInfo]
    methodology: str
    origin: str | None = None
    airport_name: str | None = None
    threshold_miles: float | None = None
    long_haul_share_pct: float | None = None
    long_haul_average_daily_flights: float | None = None
    known_distance_average_daily_flights: float | None = None
    total_average_daily_flights: float | None = None
    coverage_pct: float | None = None
    observation_period: str | None = None
    conversation_id: str
    answer: str
