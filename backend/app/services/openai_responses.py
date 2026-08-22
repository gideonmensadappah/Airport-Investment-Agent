import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SYSTEM_INSTRUCTIONS = """You are an airport investment analysis assistant.
Use the provided tools for every new numerical analysis. The tools are the only
source of calculated values: never invent, recalculate, round differently, or
change a tool result. After a tool returns, answer in the user's language as one
plain-text paragraph with no more than two short sentences and 60 words. State
only the main conclusion and confidence. The interface separately displays the
detailed metrics, methodology, assumptions, limitations, and sources, so do not
repeat them. Mention only fields present in the tool output. Do not add headings,
lists, follow-up offers, or capabilities the tools do not provide. Attribute all
calculations to the analysis tool or deterministic service, never to the model.
For a follow-up about an existing result, answer from the conversation context
without calling a tool unless the user requests a new or changed analysis. Keep
follow-ups to the same two-sentence limit. If required locations or airports are
ambiguous or missing, ask one short clarification question instead of guessing.
Airport arguments must be three-letter IATA codes.
Long-haul is defined by the analysis tool as at least 3,000 statute miles; do
not ask the user to choose a threshold.
"""


TOOLS = [
    {
        "type": "function",
        "name": "compare_congestion",
        "description": (
            "Compare operational congestion for two to six US airports using "
            "deterministic delay and cancellation metrics."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "airports": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[A-Z]{3}$"},
                    "minItems": 2,
                    "maxItems": 6,
                }
            },
            "required": ["airports"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analyze_unmet_demand",
        "description": (
            "Rank potential nonstop route opportunities from one origin airport "
            "using the bundled US DOT DB1C demand snapshot."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "airport": {"type": "string", "pattern": "^[A-Z]{3}$"},
                "top_n": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["airport", "top_n"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "analyze_long_haul_share",
        "description": (
            "Calculate the departure-frequency-weighted percentage of flights "
            "from one airport that travel at least 3,000 statute miles."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "airport": {"type": "string", "pattern": "^[A-Z]{3}$"},
            },
            "required": ["airport"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "rank_expansion_candidates",
        "description": (
            "Rank airports in a supported US region by deterministic expansion "
            "opportunity score."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "region": {"type": "string", "minLength": 2, "maxLength": 100},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["region", "limit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


class OpenAIResponsesError(RuntimeError):
    """Raised when the Responses API cannot provide a usable response."""


@dataclass(frozen=True)
class FunctionCall:
    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ModelResponse:
    id: str
    text: str
    function_calls: tuple[FunctionCall, ...]


class OpenAIResponsesClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = f"{base_url.rstrip('/')}/responses"
        self.timeout_seconds = timeout_seconds

    def start(self, message: str, previous_response_id: str | None = None) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": message,
            "tools": TOOLS,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        }
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        return self._create(payload)

    def submit_tool_output(
        self,
        previous_response_id: str,
        call_id: str,
        output: str,
    ) -> ModelResponse:
        return self._create(
            {
                "model": self.model,
                "instructions": SYSTEM_INSTRUCTIONS,
                "previous_response_id": previous_response_id,
                "input": [
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": output,
                    }
                ],
                "tools": TOOLS,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "max_output_tokens": 400,
            }
        )

    def _create(self, payload: dict[str, Any]) -> ModelResponse:
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise OpenAIResponsesError(
                f"OpenAI Responses API returned HTTP {exc.code}."
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OpenAIResponsesError("OpenAI Responses API request failed.") from exc

        return _parse_response(body)


def _parse_response(body: dict[str, Any]) -> ModelResponse:
    response_id = body.get("id")
    if not isinstance(response_id, str) or not response_id:
        raise OpenAIResponsesError("OpenAI response did not include an id.")

    text_parts: list[str] = []
    calls: list[FunctionCall] = []
    for item in body.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "function_call":
            call_id = item.get("call_id")
            name = item.get("name")
            arguments = item.get("arguments")
            if all(isinstance(value, str) for value in (call_id, name, arguments)):
                calls.append(FunctionCall(call_id, name, arguments))
        if item.get("type") == "message":
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())

    return ModelResponse(
        id=response_id,
        text="\n\n".join(text_parts),
        function_calls=tuple(calls),
    )
