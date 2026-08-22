import json
import logging
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

from pydantic import ValidationError

from app.models.analysis import (
    AnalysisResponse,
    ChatResponse,
    DemandAnalysisResponse,
    LongHaulAnalysisResponse,
)
from app.models.tool_calls import (
    AnalyzeLongHaulArguments,
    AnalyzeLongHaulToolCall,
    AnalyzeUnmetDemandArguments,
    AnalyzeUnmetDemandToolCall,
    ClarificationDecision,
    CompareCongestionArguments,
    CompareCongestionToolCall,
    RankExpansionCandidatesArguments,
    RankExpansionCandidatesToolCall,
    RoutingDecision,
)
from app.services.analysis import AnalysisService
from app.services.demand import DemandService
from app.services.intent_router import IntentRouter
from app.services.long_haul import LongHaulService
from app.services.openai_responses import (
    FunctionCall,
    OpenAIResponsesClient,
    OpenAIResponsesError,
)


logger = logging.getLogger(__name__)


class UnsupportedQuestionError(ValueError):
    pass


AnalysisResult = AnalysisResponse | DemandAnalysisResponse | LongHaulAnalysisResponse


@dataclass
class ConversationState:
    previous_response_id: str
    last_result: AnalysisResult


class ChatService:
    def __init__(
        self,
        analysis: AnalysisService,
        demand: DemandService,
        long_haul: LongHaulService,
        intent_router: IntentRouter,
        llm: OpenAIResponsesClient | None = None,
        max_conversations: int = 500,
    ) -> None:
        self.analysis = analysis
        self.demand = demand
        self.long_haul = long_haul
        self.intent_router = intent_router
        self.llm = llm
        self.max_conversations = max_conversations
        self._conversations: OrderedDict[str, ConversationState] = OrderedDict()
        self._conversation_lock = RLock()

    def answer(self, message: str, conversation_id: str | None = None) -> ChatResponse:
        resolved_conversation_id = conversation_id or str(uuid4())
        if self.llm is not None:
            try:
                return self._answer_with_llm(message, resolved_conversation_id)
            except OpenAIResponsesError:
                # The deterministic router keeps the core analysis available if
                # the external model is unavailable.
                logger.warning(
                    "OpenAI orchestration failed; using deterministic routing.",
                    exc_info=True,
                )

        decision = self.intent_router.route(message)

        result = self._execute(decision)
        return self._to_chat_response(
            result,
            resolved_conversation_id,
            answer=result.summary,
        )

    def _answer_with_llm(self, message: str, conversation_id: str) -> ChatResponse:
        state = self._get_state(conversation_id)
        response = self.llm.start(
            message,
            previous_response_id=state.previous_response_id if state else None,
        )

        if not response.function_calls:
            if state is None:
                raise UnsupportedQuestionError(
                    response.text or "Please specify an airport analysis request."
                )
            self._save_state(conversation_id, response.id, state.last_result)
            return self._to_chat_response(
                state.last_result,
                conversation_id,
                answer=response.text or state.last_result.summary,
            )

        if len(response.function_calls) != 1:
            raise OpenAIResponsesError("Expected exactly one analysis tool call.")

        decision = self._decision_from_function_call(response.function_calls[0])
        result = self._execute(decision)
        final_response = self.llm.submit_tool_output(
            previous_response_id=response.id,
            call_id=response.function_calls[0].call_id,
            output=result.model_dump_json(),
        )
        if final_response.function_calls:
            raise OpenAIResponsesError("The model exceeded the one-tool-call limit.")

        self._save_state(conversation_id, final_response.id, result)
        return self._to_chat_response(
            result,
            conversation_id,
            answer=final_response.text or result.summary,
        )

    @staticmethod
    def _decision_from_function_call(call: FunctionCall) -> RoutingDecision:
        argument_models = {
            "compare_congestion": CompareCongestionArguments,
            "analyze_unmet_demand": AnalyzeUnmetDemandArguments,
            "rank_expansion_candidates": RankExpansionCandidatesArguments,
            "analyze_long_haul_share": AnalyzeLongHaulArguments,
        }
        model = argument_models.get(call.name)
        if model is None:
            raise OpenAIResponsesError(f"Unknown tool requested: {call.name}.")
        try:
            arguments = model.model_validate(json.loads(call.arguments))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise OpenAIResponsesError("The model returned invalid tool arguments.") from exc

        if call.name == "compare_congestion":
            return CompareCongestionToolCall(arguments=arguments)
        if call.name == "analyze_unmet_demand":
            return AnalyzeUnmetDemandToolCall(arguments=arguments)
        if call.name == "analyze_long_haul_share":
            return AnalyzeLongHaulToolCall(arguments=arguments)
        return RankExpansionCandidatesToolCall(arguments=arguments)

    def _execute(self, decision: RoutingDecision) -> AnalysisResult:

        if isinstance(decision, ClarificationDecision):
            raise UnsupportedQuestionError(decision.message)

        if isinstance(decision, AnalyzeUnmetDemandToolCall):
            result = self.demand.analyze_unmet_demand(
                decision.arguments.airport,
                top_n=decision.arguments.top_n,
            )
        elif isinstance(decision, AnalyzeLongHaulToolCall):
            result = self.long_haul.analyze_long_haul_share(
                decision.arguments.airport,
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

        return result

    @staticmethod
    def _to_chat_response(
        result: AnalysisResult,
        conversation_id: str,
        answer: str,
    ) -> ChatResponse:
        return ChatResponse(
            **result.model_dump(),
            conversation_id=conversation_id,
            answer=answer,
        )

    def _get_state(self, conversation_id: str) -> ConversationState | None:
        with self._conversation_lock:
            state = self._conversations.get(conversation_id)
            if state is not None:
                self._conversations.move_to_end(conversation_id)
            return state

    def _save_state(
        self,
        conversation_id: str,
        previous_response_id: str,
        result: AnalysisResult,
    ) -> None:
        with self._conversation_lock:
            self._conversations[conversation_id] = ConversationState(
                previous_response_id=previous_response_id,
                last_result=result,
            )
            self._conversations.move_to_end(conversation_id)
            while len(self._conversations) > self.max_conversations:
                self._conversations.popitem(last=False)
