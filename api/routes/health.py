"""
Health & Capabilities Routes
"""
from fastapi import APIRouter, Depends
from api.dependencies import get_ai_service
from api.schemas import HealthResponse, CapabilitiesResponse
from src.integration.service import LearningIntelligenceModule

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
def get_health(ai: LearningIntelligenceModule = Depends(get_ai_service)):
    """Health check for AI subsystems, LLM providers, search, and storage."""
    h = ai.health()
    return HealthResponse(status="ok", ai_status=h)


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(ai: LearningIntelligenceModule = Depends(get_ai_service)):
    """Exposes system capabilities, supported content types, and supported languages."""
    c = ai.get_supported_capabilities()
    return CapabilitiesResponse(
        active_providers=c.get("active_providers", []),
        mock_providers=c.get("mock_providers", []),
        multi_provider_mode=c.get("multi_provider_mode", False),
        content_types=c.get("content_types", []),
        unsupported_without_multimedia_provider=c.get("unsupported_without_multimedia_provider", []),
        languages=c.get("languages", []),
        ocr=c.get("ocr", False),
        realtime_voice=c.get("realtime_voice", False),
        neural_embeddings=c.get("neural_embeddings", False),
    )
