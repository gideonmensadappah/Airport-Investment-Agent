from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.models.analysis import ChatRequest, ChatResponse
from app.services.airport_data import AeroDataBoxClient, AirportRepository
from app.services.airport_resolver import AirportResolver
from app.services.analysis import AnalysisService
from app.services.chat import ChatService, UnsupportedQuestionError
from app.services.demand import DemandService
from app.services.intent_router import IntentRouter
from app.services.openai_responses import OpenAIResponsesClient

router = APIRouter(prefix="/chat", tags=["chat"])

repository = AirportRepository()
aerodatabox = AeroDataBoxClient(
    api_key=settings.aerodatabox_api_key,
    base_url=settings.aerodatabox_base_url,
    rapidapi_host=settings.aerodatabox_rapidapi_host,
    timeout_seconds=settings.aerodatabox_timeout_seconds,
)

analysis_service = AnalysisService(
    repository=repository,
    aerodatabox=aerodatabox,
    use_live_data=settings.use_aerodatabox,
)
demand_service = DemandService(database_file=settings.airport_database_file)
airport_resolver = AirportResolver(
    supported_codes=repository.supported_codes,
    supported_regions=repository.supported_regions,
)
intent_router = IntentRouter(airport_resolver)
openai_client = (
    OpenAIResponsesClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        timeout_seconds=settings.openai_timeout_seconds,
    )
    if settings.use_openai and settings.openai_api_key
    else None
)
chat_service = ChatService(
    analysis_service,
    demand_service,
    intent_router,
    llm=openai_client,
)


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return chat_service.answer(request.message, request.conversation_id)
    except (UnsupportedQuestionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
