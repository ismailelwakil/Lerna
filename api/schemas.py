"""
Academic OS - API Data Transfer Schemas (Pydantic v2)
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# Health & Capabilities
# -------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
    ai_status: Dict[str, Any]


class CapabilitiesResponse(BaseModel):
    active_providers: List[str] = Field(default_factory=list)
    mock_providers: List[str] = Field(default_factory=list)
    multi_provider_mode: bool = False
    content_types: List[str] = Field(default_factory=list)
    unsupported_without_multimedia_provider: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    ocr: bool = False
    realtime_voice: bool = False
    neural_embeddings: bool = False


# -------------------------------------------------------------
# Student Profile & Learning State
# -------------------------------------------------------------
class StudentPreferencesUpdate(BaseModel):
    name: Optional[str] = None
    course: Optional[str] = None
    preferred_language: Optional[str] = None
    learning_preference: Optional[str] = None


class StudentProfileData(BaseModel):
    student_id: str
    name: str
    course: str
    preferred_language: str
    learning_preference: str
    concept_mastery: Dict[str, float] = Field(default_factory=dict)
    weak_concepts: List[str] = Field(default_factory=list)
    unknown_concepts: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    prerequisite_gaps: List[str] = Field(default_factory=list)
    recent_topics: List[str] = Field(default_factory=list)


class NextBestActionData(BaseModel):
    action: str
    reason: str
    target_concepts: List[str] = Field(default_factory=list)
    strategy: str
    recommended_resources: List[str] = Field(default_factory=list)
    priority: str
    triggering_evidence: Optional[str] = None


class StudyPlanItem(BaseModel):
    title: str
    concept: str
    priority: str
    reason: str
    recommended_actions: List[str] = Field(default_factory=list)
    completed: bool = False


class SpacedReviewItem(BaseModel):
    concept: str
    due_date: str
    interval_days: float
    repetition: int
    ease_factor: float
    last_reviewed: Optional[str] = None
    mastery: float = 0.0


class LearningStateResponse(BaseModel):
    profile: StudentProfileData
    next_action: Optional[NextBestActionData] = None
    study_plan: List[StudyPlanItem] = Field(default_factory=list)
    review_queue: List[SpacedReviewItem] = Field(default_factory=list)
    learning_history: List[Dict[str, Any]] = Field(default_factory=list)


# -------------------------------------------------------------
# AI Tutor
# -------------------------------------------------------------
class TutorChatRequest(BaseModel):
    student_id: Optional[str] = None
    course_id: Optional[str] = "General"
    message: str
    language: Optional[str] = "en"
    document_ids: Optional[List[str]] = None
    tutoring_style: Optional[str] = "direct"  # "direct" or "socratic"
    session_id: Optional[str] = "web-session"
    chat_history: Optional[List[Dict[str, Any]]] = None


class CitationModel(BaseModel):
    citation_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source: str
    source_type: str = "trusted_external"
    authority: Optional[str] = "university"
    trust_score: float = 1.0
    url: Optional[str] = None
    page: Optional[int] = None
    excerpt: Optional[str] = None
    title: Optional[str] = None


class TutorChatResponse(BaseModel):
    answer: str
    evidence: List[CitationModel] = Field(default_factory=list)
    abstained: bool = False
    search_state: Optional[str] = None
    source_type: str = "trusted_external"
    evidence_limitation: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


# -------------------------------------------------------------
# Course Materials
# -------------------------------------------------------------
class MaterialModel(BaseModel):
    document_id: str
    filename: str
    course: str
    upload_date: Optional[str] = None
    status: str = "indexed"
    chunk_count: int = 1
    source_type: str = "student_upload"


class MaterialsListResponse(BaseModel):
    materials: List[MaterialModel] = Field(default_factory=list)


class MaterialUploadResponse(BaseModel):
    document_id: str
    filename: str
    course: str
    chunk_count: int
    status: str = "indexed"
    message: str = "File successfully uploaded and indexed into knowledge base."


# -------------------------------------------------------------
# Study Tools / Content Generation
# -------------------------------------------------------------
class StudyToolsGenerateRequest(BaseModel):
    student_id: Optional[str] = None
    topic: str
    kinds: List[str]
    language: Optional[str] = "en"
    document_ids: Optional[List[str]] = None


class GeneratedResourceModel(BaseModel):
    type: str  # "text", "file", "unavailable"
    kind: str
    content: Optional[str] = None
    path: Optional[str] = None
    filename: Optional[str] = None
    download_url: Optional[str] = None
    mime_type: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    source_type: str = "trusted_external"
    learner_state: Optional[str] = None
    teaching_strategy: Optional[str] = None
    evidence_limitation: Optional[str] = None
    message: Optional[str] = None


class StudyToolsGenerateResponse(BaseModel):
    topic: str
    resources: Dict[str, GeneratedResourceModel]


# -------------------------------------------------------------
# Assessment / Diagnostic
# -------------------------------------------------------------
class AssessmentGenerateRequest(BaseModel):
    student_id: Optional[str] = None
    topic: str
    language: Optional[str] = "en"
    document_ids: Optional[List[str]] = None


class AssessmentQuestionModel(BaseModel):
    question_id: str
    concept: str
    kind: str  # "mcq" or "short"
    prompt: str
    options: List[str] = Field(default_factory=list)
    difficulty: str = "medium"
    source_type: str = "trusted_external"
    source_title: str = "Authoritative Sources"


class AssessmentGenerateResponse(BaseModel):
    assessment_id: str
    topic: str
    questions: List[AssessmentQuestionModel]
    source_type: str
    source_title: str


class AssessmentSubmitRequest(BaseModel):
    student_id: Optional[str] = None
    answers: Dict[str, str]
    language: Optional[str] = "en"


class AssessmentSubmitResponse(BaseModel):
    assessment_id: str
    score: float
    concept_mastery: Dict[str, float]
    weak_concepts: List[str]
    unknown_concepts: List[str]
    strengths: List[str]
    recommendations: List[str]
    feedback_per_question: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Spaced Repetition
# -------------------------------------------------------------
class SpacedReviewRequest(BaseModel):
    student_id: Optional[str] = None
    concept: str
    remembered: bool


class SpacedReviewResponse(BaseModel):
    success: bool
    concept: str
    remembered: bool
    next_review_date: Optional[str] = None
    interval_days: Optional[float] = None
    mastery: Optional[float] = None
