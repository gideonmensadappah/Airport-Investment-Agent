from uuid import uuid4

from app.models.analysis import ChatResponse
from app.models.tool_calls import (
    AnalyzeUnmetDemandToolCall,
    ClarificationDecision,
    CompareCongestionToolCall,
    RankExpansionCandidatesToolCall,
)
from app.services.analysis import AnalysisService
from app.services.demand import DemandService
from app.services.intent_router import IntentRouter


class UnsupportedQuestionError(ValueError):
    pass


class ChatService:
    def __init__(
        self,
        analysis: AnalysisService,
        demand: DemandService,
        intent_router: IntentRouter,
    ) -> None:
        self.analysis = analysis
        self.demand = demand
        self.intent_router = intent_router

    def answer(self, message: str, conversation_id: str | None = None) -> ChatResponse:
        decision = self.intent_router.route(message)

        if isinstance(decision, ClarificationDecision):
            raise UnsupportedQuestionError(decision.message)

        if isinstance(decision, AnalyzeUnmetDemandToolCall):
            result = self.demand.analyze_unmet_demand(
                decision.arguments.airport,
                top_n=decision.arguments.top_n,
            )
        elif isinstance(decision, CompareCongestionToolCall):
            result = self.analysis.compare_congestion(decision.arguments.airports)
        elif isinstance(decision, RankExpansionCandidatesToolCall):
            result = self.analysis.rank_expansion_candidates(
                region=decision.arguments.region,
                limit=decision.arguments.limit,
            )
        else:
            raise RuntimeError(f"Unhandled routing decision: {type(decision).__name__}")

        return ChatResponse(
            **result.model_dump(),
            conversation_id=conversation_id or str(uuid4()),
            answer=result.summary,
        )
