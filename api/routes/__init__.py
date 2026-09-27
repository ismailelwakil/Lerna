"""
API Route Handlers
"""
from .health import router as health_router
from .profile import router as profile_router
from .tutor import router as tutor_router
from .materials import router as materials_router
from .study_tools import router as study_tools_router
from .assessments import router as assessments_router
from .spaced_repetition import router as spaced_repetition_router
from .artifacts import router as artifacts_router
from .platform import router as platform_router

__all__ = [
    "health_router",
    "profile_router",
    "tutor_router",
    "materials_router",
    "study_tools_router",
    "assessments_router",
    "spaced_repetition_router",
    "artifacts_router",
    "platform_router",
]
