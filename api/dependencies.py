"""
Academic OS - Thin API Dependencies & AI Module Injection
"""
import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import Header, HTTPException

# Ensure ai-service root is in Python module search path
AI_SERVICE_DIR = Path(__file__).resolve().parent.parent / "ai-service"
if AI_SERVICE_DIR.exists() and str(AI_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_DIR))

# Fallback: if running directly from ai-service directory
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from src.integration.service import build_module, LearningIntelligenceModule

_AI_INSTANCE: Optional[LearningIntelligenceModule] = None


def get_ai_service() -> LearningIntelligenceModule:
    """
    Returns the singleton LearningIntelligenceModule instance.
    Loads real providers from .env if available, falls back gracefully.
    """
    global _AI_INSTANCE
    if _AI_INSTANCE is None:
        # Check if running in test mode
        test_mode = os.getenv("ACADEMIC_OS_TEST_MODE", "false").lower() == "true"
        data_dir = os.getenv("ACADEMIC_OS_DATA_DIR")
        if not data_dir:
            # Default to ai-service/data
            data_dir_path = AI_SERVICE_DIR / "data"
            if data_dir_path.exists():
                data_dir = str(data_dir_path)
        _AI_INSTANCE = build_module(data_dir=data_dir, test_mode=test_mode)
    return _AI_INSTANCE


def get_current_student_id(
    authorization: Optional[str] = Header(None),
    x_student_id: Optional[str] = Header(None, alias="X-Student-Id"),
) -> str:
    """
    Auth-ready identity resolver.
    In the current handoff phase, maps Authorization Bearer token or X-Student-Id header
    to the active student ID, defaulting to 'student-001'.
    A production backend can easily replace this with JWT verification.
    """
    if x_student_id:
        return x_student_id.strip()

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
        # In a production backend: decode JWT and return user.student_id
        if token and token != "mock-token":
            return token

    # Default fallback for demo / developer handoff
    return os.getenv("DEFAULT_STUDENT_ID", "student-001")
