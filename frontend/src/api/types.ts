/**
 * Academic OS - Frontend TypeScript API Contracts
 * Maps strictly to Backend Pydantic Schemas
 */

export interface StudentProfile {
  student_id: string;
  name: string;
  course: string;
  preferred_language: string;
  learning_preference: string;
  concept_mastery: Record<string, number>;
  weak_concepts: string[];
  unknown_concepts: string[];
  strengths: string[];
  misconceptions: string[];
  prerequisite_gaps: string[];
  recent_topics: string[];
}

export interface StudentPreferencesUpdate {
  name?: string;
  course?: string;
  preferred_language?: string;
  learning_preference?: string;
}

export interface NextBestAction {
  action: string;
  reason: string;
  target_concepts: string[];
  strategy: string;
  recommended_resources: string[];
  priority: 'high' | 'medium' | 'low' | string;
  triggering_evidence?: string | null;
}

export interface StudyPlanItem {
  title: string;
  concept: string;
  priority: 'high' | 'medium' | 'low' | string;
  reason: string;
  recommended_actions: string[];
  completed: boolean;
}

export interface SpacedReviewItem {
  concept: string;
  due_date: string;
  interval_days: number;
  repetition: number;
  ease_factor: number;
  last_reviewed?: string | null;
  mastery: number;
}

export interface LearningActivityItem {
  timestamp?: string;
  topic?: string;
  query?: string;
  language?: string;
  confidence?: number;
  knowledge_source?: string;
  trusted_search_state?: string;
  [key: string]: unknown;
}

export interface LearningState {
  profile: StudentProfile;
  next_action?: NextBestAction | null;
  study_plan: StudyPlanItem[];
  review_queue: SpacedReviewItem[];
  learning_history: LearningActivityItem[];
}

export interface Citation {
  citation_id?: string;
  chunk_id?: string;
  source: string;
  source_type: 'trusted_external' | 'student_upload' | string;
  authority?: string;
  trust_score: number;
  url?: string | null;
  page?: number | null;
  excerpt?: string | null;
  title?: string | null;
}

export interface TutorChatRequest {
  student_id?: string;
  course_id?: string;
  message: string;
  language?: string;
  document_ids?: string[] | null;
  tutoring_style?: 'direct' | 'socratic';
  session_id?: string;
  chat_history?: Array<{ role: string; content: string }>;
}

export interface TutorChatResponse {
  answer: string;
  evidence: Citation[];
  abstained: boolean;
  search_state?: string | null;
  source_type: 'trusted_external' | 'student_upload' | string;
  evidence_limitation?: string | null;
  diagnostics: Record<string, unknown>;
}

export interface Material {
  document_id: string;
  filename: string;
  course: string;
  upload_date?: string | null;
  status: 'indexed' | 'processing' | 'failed' | string;
  chunk_count: number;
  source_type: 'student_upload';
}

export interface MaterialsListResponse {
  materials: Material[];
}

export interface MaterialUploadResponse {
  document_id: string;
  filename: string;
  course: string;
  chunk_count: number;
  status: string;
  message: string;
}

export interface GeneratedResource {
  type: 'text' | 'file' | 'unavailable' | string;
  kind: string;
  content?: string | null;
  path?: string | null;
  filename?: string | null;
  download_url?: string | null;
  mime_type?: string | null;
  sources: string[];
  source_type: string;
  learner_state?: string | null;
  teaching_strategy?: string | null;
  evidence_limitation?: string | null;
  message?: string | null;
}

export interface StudyToolsGenerateRequest {
  student_id?: string;
  topic: string;
  kinds: string[];
  language?: string;
  document_ids?: string[] | null;
}

export interface StudyToolsGenerateResponse {
  topic: string;
  resources: Record<string, GeneratedResource>;
}

export interface AssessmentQuestion {
  question_id: string;
  concept: string;
  kind: 'mcq' | 'short' | string;
  prompt: string;
  options: string[];
  difficulty: string;
  source_type: string;
  source_title: string;
}

export interface AssessmentGenerateRequest {
  student_id?: string;
  topic: string;
  language?: string;
  document_ids?: string[] | null;
}

export interface AssessmentGenerateResponse {
  assessment_id: string;
  topic: string;
  questions: AssessmentQuestion[];
  source_type: string;
  source_title: string;
}

export interface QuestionFeedback {
  concept: string;
  student_answer: string;
  expected_answer: string;
  is_correct: boolean;
  is_idk: boolean;
  rubric: string;
}

export interface AssessmentSubmitRequest {
  student_id?: string;
  answers: Record<string, string>;
  language?: string;
}

export interface AssessmentSubmitResponse {
  assessment_id: string;
  score: number;
  concept_mastery: Record<string, number>;
  weak_concepts: string[];
  unknown_concepts: string[];
  strengths: string[];
  recommendations: string[];
  feedback_per_question?: Record<string, QuestionFeedback>;
}

export interface SpacedReviewRequest {
  student_id?: string;
  concept: string;
  remembered: boolean;
}

export interface SpacedReviewResponse {
  success: boolean;
  concept: string;
  remembered: boolean;
  next_review_date?: string | null;
  interval_days?: number | null;
  mastery?: number | null;
}

export interface SystemCapabilities {
  active_providers: string[];
  mock_providers: string[];
  multi_provider_mode: boolean;
  content_types: string[];
  unsupported_without_multimedia_provider: string[];
  languages: string[];
  ocr: boolean;
  realtime_voice: boolean;
  neural_embeddings: boolean;
}

export interface HealthStatus {
  status: string;
  ai_status: Record<string, unknown>;
}
