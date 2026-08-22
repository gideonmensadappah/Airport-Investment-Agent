import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompareCongestionArguments(ToolArguments):
    airports: list[str] = Field(min_length=2, max_length=6)

    @field_validator("airports")
    @classmethod
    def validate_airports(cls, airports: list[str]) -> list[str]:
        normalized = [_normalize_iata(code) for code in airports]
        if len(set(normalized)) != len(normalized):
            raise ValueError("airports must contain unique IATA codes")
        return normalized


class AnalyzeUnmetDemandArguments(ToolArguments):
    airport: str
    top_n: int = Field(default=5, ge=1, le=10)

    @field_validator("airport")
    @classmethod
    def validate_airport(cls, airport: str) -> str:
        return _normalize_iata(airport)


class RankExpansionCandidatesArguments(ToolArguments):
    region: str = Field(min_length=2, max_length=100)
    limit: int = Field(default=5, ge=1, le=10)

    @field_validator("region")
    @classmethod
    def normalize_region(cls, region: str) -> str:
        return " ".join(region.split())


class AnalyzeLongHaulArguments(ToolArguments):
    airport: str

    @field_validator("airport")
    @classmethod
    def validate_airport(cls, airport: str) -> str:
        return _normalize_iata(airport)


class CompareCongestionToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["compare_congestion"] = "compare_congestion"
    arguments: CompareCongestionArguments


class AnalyzeUnmetDemandToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["analyze_unmet_demand"] = "analyze_unmet_demand"
    arguments: AnalyzeUnmetDemandArguments


class RankExpansionCandidatesToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["rank_expansion_candidates"] = "rank_expansion_candidates"
    arguments: RankExpansionCandidatesArguments


class AnalyzeLongHaulToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["analyze_long_haul_share"] = "analyze_long_haul_share"
    arguments: AnalyzeLongHaulArguments


class ClarificationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["clarification"] = "clarification"
    message: str = Field(min_length=1)


RoutingDecision = (
    CompareCongestionToolCall
    | AnalyzeUnmetDemandToolCall
    | RankExpansionCandidatesToolCall
    | AnalyzeLongHaulToolCall
    | ClarificationDecision
)


def _normalize_iata(code: str) -> str:
    normalized = code.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", normalized):
        raise ValueError("airport must be a three-letter IATA code")
    return normalized
