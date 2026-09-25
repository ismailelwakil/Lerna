from datetime import datetime, timezone
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

SUPPORTED_LANGUAGES = ('en','ar','fr','sw','ha','am','so','yo','ig','zu')

class Student(Strict):
    student_id: str
    name: str
    course: str = 'General'
    preferred_language: str = 'en'
    learning_preference: str = 'step-by-step'

class ChatTurn(Strict):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=2000)

class StudentQuery(Strict):
    student_id: str
    session_id: str
    text: str = Field(min_length=1)
    course: str = 'General'
    preferred_language: str | None = None
    document_ids: list[str] | None = None
    chat_history: list[ChatTurn] | None = None

    @field_validator('chat_history', mode='before')
    @classmethod
    def _validate_chat_history(cls, v):
        if v is None:
            return None
        cleaned = []
        for item in v:
            if isinstance(item, dict):
                role = item.get('role')
                if role not in ('user', 'assistant'):
                    continue
                raw_content = item.get('content') or item.get('text') or ''
                content = str(raw_content).strip()
                if not content:
                    continue
                cleaned.append(ChatTurn(role=role, content=content[:2000]))
            elif isinstance(item, ChatTurn):
                cleaned.append(item)
        return cleaned[-4:]

class LanguageResult(Strict):
    language: str
    confidence: float = Field(ge=0, le=1)
    normalized_text: str
    original_text: str
    normalized_english_query: str | None = None
    detected_variant: str | None = None
    script: str = 'Latin'
    direction: Literal['ltr','rtl'] = 'ltr'
    supported: bool = True

class QueryAnalysis(Strict):
    intent: str
    domain: str
    topic: str
    concepts: list[str]
    prerequisites: list[str]
    requested_outputs: list[str]
    difficulty: str
    retrieval_required: bool
    assessment_required: bool
    personalization_required: bool
    code_needed: bool
    source_mode: Literal['uploaded_material','trusted_external'] = 'trusted_external'
    trusted_discovery_required: bool = True

class DocumentMeta(Strict):
    document_id: str
    filename: str
    source_type: str = 'student_upload'
    owner_id: str
    pages: int = 1
    chunks: int = 0
    indexed: bool = False
    source_url: str | None = None
    publisher: str | None = None
    trust_score: float = 1.0
    course: str = 'General'
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class Chunk(Strict):
    chunk_id: str
    document_id: str
    text: str
    source: str
    page: int | None = None
    slide: int | None = None
    section: str | None = None
    authority: str = 'student_upload'
    trust_score: float = 1.0
    owner_id: str | None = None
    language: str = 'unknown'
    source_type: str = 'student_upload'
    source_url: str | None = None
    publisher: str | None = None
    course: str = 'General'

class Evidence(Strict):
    chunk_id: str
    text: str
    source: str
    score: float
    authority: str
    trust_score: float
    page: int | None = None
    source_type: str = 'unknown'
    source_url: str | None = None
    conflict: bool = False
    retrieval_method: str = 'hybrid'
    is_wikipedia: bool = False

class AssessmentQuestion(Strict):
    question_id: str
    concept: str
    kind: Literal['mcq','short','true_false','code']
    prompt: str
    options: list[str] = Field(default_factory=list)
    expected: str
    prerequisite_concepts: list[str] = Field(default_factory=list)
    difficulty: str = 'adaptive'
    rubric: str | None = None
    misconception_targets: list[str] = Field(default_factory=list)
    source_type: Literal['student_upload', 'trusted_external'] | None = None
    source_title: str | None = None
    document_id: str | None = None
    source_url: str | None = None
    evidence_chunk_ids: list[str] = Field(default_factory=list)
    evidence_excerpt: str | None = None
    trust_score: float | None = None
    verification_method: Literal['deterministic_trace', 'complexity_notation', 'exact_evidence_fact', 'semantic_rubric'] | None = None

class Assessment(Strict):
    assessment_id: str
    topic: str
    questions: list[AssessmentQuestion]
    source_type: Literal['student_upload', 'trusted_external'] | None = None
    source_title: str | None = None

class AssessmentResult(Strict):
    assessment_id: str
    score: float
    concept_mastery: dict[str,float]
    weak_concepts: list[str]
    prerequisite_gaps: list[str]
    misconceptions: list[str]
    strengths: list[str]
    recommendations: list[str]
    unknown_concepts: list[str] = Field(default_factory=list)
    source_type: Literal['student_upload', 'trusted_external'] | None = None
    source_title: str | None = None

class StudentProfile(Strict):
    student: Student
    concept_mastery: dict[str,float] = Field(default_factory=dict)
    weak_concepts: list[str] = Field(default_factory=list)
    prerequisite_gaps: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    resolved_misconceptions: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    unknown_concepts: list[str] = Field(default_factory=list)
    assessment_history: list[dict[str,Any]] = Field(default_factory=list)
    learning_history: list[dict[str,Any]] = Field(default_factory=list)
    recent_topics: list[str] = Field(default_factory=list)
    generated_resources: list[dict[str,Any]] = Field(default_factory=list)
    review_queue: list[dict[str,Any]] = Field(default_factory=list)
    study_plan: list[dict[str,Any]] = Field(default_factory=list)
    conversation_history: list[dict[str,Any]] = Field(default_factory=list)
    learning_goal: str | None = None
    concept_confidence: dict[str,float] = Field(default_factory=dict)
    concept_exposure_count: dict[str,int] = Field(default_factory=dict)
    concept_evidence_count: dict[str,int] = Field(default_factory=dict)
    last_assessed_at: dict[str,str] = Field(default_factory=dict)
    performance_trend: list[float] = Field(default_factory=list)

class RoutingDecision(Strict):
    task: str
    capability: str
    provider: str
    model: str
    routing_score: float
    fallback: bool = False
    validation_state: str = 'pending'
    language_fit: float = 1.0

class TutorResponse(Strict):
    request_id: str
    language: LanguageResult
    analysis: QueryAnalysis
    answer: str
    evidence: list[Evidence]
    confidence: float
    citations: list[str]
    abstained: bool = False
    conflict_detected: bool = False
    routing: list[RoutingDecision] = Field(default_factory=list)
    assessment: Assessment | None = None
    knowledge_source: str = 'unknown'
    trusted_search_state: str = 'not_required'

class ReviewItem(Strict):
    concept: str
    due_date: str
    interval_days: float
    repetition: int = 0
    ease_factor: float = 2.5
    last_reviewed: str | None = None
    mastery: float = 0.0

class StudyPlanItem(Strict):
    title: str
    concept: str
    priority: Literal['high', 'medium', 'low']
    reason: str
    recommended_actions: list[str] = Field(default_factory=list)
    completed: bool = False

class VoiceResult(Strict):
    request_id: str
    student_id: str
    transcription: str
    answer: str
    audio_path: str | None = None
    tutor_response: TutorResponse
    success: bool = True
    error_message: str | None = None
    stt_provider: str = 'local'
    tts_provider: str = 'local'
