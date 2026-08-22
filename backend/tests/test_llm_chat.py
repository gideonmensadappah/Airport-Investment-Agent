import json
import unittest

from app.services.airport_data import AeroDataBoxClient, AirportRepository
from app.services.airport_resolver import AirportResolver
from app.services.analysis import AnalysisService
from app.services.chat import ChatService
from app.services.demand import DemandService
from app.services.intent_router import IntentRouter
from app.services.long_haul import LongHaulService
from app.services.openai_responses import FunctionCall, ModelResponse


class FakeResponsesClient:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = iter(responses)
        self.starts: list[tuple[str, str | None]] = []
        self.tool_outputs: list[tuple[str, str, str]] = []

    def start(self, message: str, previous_response_id: str | None = None) -> ModelResponse:
        self.starts.append((message, previous_response_id))
        return next(self.responses)

    def submit_tool_output(
        self,
        previous_response_id: str,
        call_id: str,
        output: str,
    ) -> ModelResponse:
        self.tool_outputs.append((previous_response_id, call_id, output))
        return next(self.responses)


class LLMChatTests(unittest.TestCase):
    def setUp(self) -> None:
        repository = AirportRepository()
        aerodatabox = AeroDataBoxClient(
            api_key=None,
            base_url="https://example.invalid",
            rapidapi_host="example.invalid",
        )
        analysis = AnalysisService(
            repository=repository,
            aerodatabox=aerodatabox,
            use_live_data=False,
        )
        resolver = AirportResolver(
            supported_codes=repository.supported_codes | {"ANC"},
            supported_regions=repository.supported_regions,
        )
        self.analysis = analysis
        self.demand = DemandService()
        self.long_haul = LongHaulService(aerodatabox, use_live_data=False)
        self.router = IntentRouter(resolver)

    def test_model_selects_tool_and_explains_deterministic_result(self) -> None:
        llm = FakeResponsesClient(
            [
                ModelResponse(
                    id="resp-tool",
                    text="",
                    function_calls=(
                        FunctionCall(
                            call_id="call-1",
                            name="compare_congestion",
                            arguments='{"airports":["LAX","SFO"]}',
                        ),
                    ),
                ),
                ModelResponse(
                    id="resp-final",
                    text="LAX shows the stronger operational congestion signal.",
                    function_calls=(),
                ),
            ]
        )
        service = ChatService(
            self.analysis,
            self.demand,
            self.long_haul,
            self.router,
            llm=llm,
        )

        response = service.answer("Which is more congested, LAX or SFO?", "conversation-1")

        self.assertEqual(response.tool, "compare_congestion")
        self.assertEqual(response.conversation_id, "conversation-1")
        self.assertIn("stronger operational congestion", response.answer)
        self.assertEqual(llm.tool_outputs[0][0:2], ("resp-tool", "call-1"))
        parsed_output = json.loads(llm.tool_outputs[0][2])
        self.assertEqual(parsed_output["tool"], "compare_congestion")
        self.assertEqual(
            {item["code"] for item in parsed_output["results"]},
            {"LAX", "SFO"},
        )
        self.assertNotIn("demand_growth_pct", llm.tool_outputs[0][2])
        self.assertNotIn("capacity_pressure_pct", llm.tool_outputs[0][2])
        self.assertNotIn("long_haul_share_pct", llm.tool_outputs[0][2])

    def test_follow_up_reuses_response_context_and_structured_result(self) -> None:
        llm = FakeResponsesClient(
            [
                ModelResponse(
                    id="resp-tool",
                    text="",
                    function_calls=(
                        FunctionCall(
                            call_id="call-1",
                            name="compare_congestion",
                            arguments='{"airports":["LAX","SFO"]}',
                        ),
                    ),
                ),
                ModelResponse(
                    id="resp-final",
                    text="LAX has the stronger signal.",
                    function_calls=(),
                ),
                ModelResponse(
                    id="resp-follow-up",
                    text="The gap is driven by the deterministic delay and cancellation inputs.",
                    function_calls=(),
                ),
            ]
        )
        service = ChatService(
            self.analysis,
            self.demand,
            self.long_haul,
            self.router,
            llm=llm,
        )
        first = service.answer("Compare LAX and SFO.", "conversation-1")

        follow_up = service.answer("Why?", "conversation-1")

        self.assertEqual(llm.starts[1], ("Why?", "resp-final"))
        self.assertEqual(follow_up.tool, first.tool)
        self.assertEqual(follow_up.results, first.results)
        self.assertIn("deterministic", follow_up.answer)

    def test_model_can_select_long_haul_tool(self) -> None:
        llm = FakeResponsesClient(
            [
                ModelResponse(
                    id="resp-tool",
                    text="",
                    function_calls=(
                        FunctionCall(
                            call_id="call-long-haul",
                            name="analyze_long_haul_share",
                            arguments='{"airport":"ANC"}',
                        ),
                    ),
                ),
                ModelResponse(
                    id="resp-final",
                    text="ANC's long-haul share is 19.7%.",
                    function_calls=(),
                ),
            ]
        )
        service = ChatService(
            self.analysis,
            self.demand,
            self.long_haul,
            self.router,
            llm=llm,
        )

        response = service.answer(
            "What percentage of flights out of Anchorage are long-haul?"
        )

        self.assertEqual(response.tool, "analyze_long_haul_share")
        self.assertEqual(response.origin, "ANC")
        self.assertEqual(response.long_haul_share_pct, 19.7)
        self.assertIn("19.7%", response.answer)

    def test_overlong_model_explanation_falls_back_to_deterministic_summary(self) -> None:
        llm = FakeResponsesClient(
            [
                ModelResponse(
                    id="resp-tool",
                    text="",
                    function_calls=(
                        FunctionCall(
                            call_id="call-1",
                            name="compare_congestion",
                            arguments='{"airports":["LAX","SNA"]}',
                        ),
                    ),
                ),
                ModelResponse(
                    id="resp-final",
                    text=" ".join(["irrelevant"] * 100),
                    function_calls=(),
                ),
            ]
        )
        service = ChatService(
            self.analysis,
            self.demand,
            self.long_haul,
            self.router,
            llm=llm,
        )

        response = service.answer("Compare LAX and SNA congestion.")

        self.assertEqual(
            response.answer,
            "LAX has the stronger congestion signal at 62.5/100, "
            "23.1 points above SNA.",
        )

    def test_model_explanation_is_limited_to_two_sentences(self) -> None:
        llm = FakeResponsesClient(
            [
                ModelResponse(
                    id="resp-tool",
                    text="",
                    function_calls=(
                        FunctionCall(
                            call_id="call-1",
                            name="compare_congestion",
                            arguments='{"airports":["LAX","SNA"]}',
                        ),
                    ),
                ),
                ModelResponse(
                    id="resp-final",
                    text=(
                        "LAX has the stronger signal. Confidence is low. "
                        "Would you like an unsupported follow-up?"
                    ),
                    function_calls=(),
                ),
            ]
        )
        service = ChatService(
            self.analysis,
            self.demand,
            self.long_haul,
            self.router,
            llm=llm,
        )

        response = service.answer("Compare LAX and SNA congestion.")

        self.assertEqual(
            response.answer,
            "LAX has the stronger signal. Confidence is low.",
        )


if __name__ == "__main__":
    unittest.main()
