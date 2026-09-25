from __future__ import annotations
from typing import Iterable, Any
from src.contracts.models import StudentQuery
from src.orchestration.factory import build_system
from src.content_context import build_content_creation_context
from src.student_intelligence.spaced_repetition import SpacedRepetitionService
from src.student_intelligence.planner import StudyPlannerService
from src.voice.service import VoiceTutorService

class LearningIntelligenceModule:
    def __init__(self, tutor):
        self.tutor = tutor
        self.spaced_repetition = SpacedRepetitionService()
        self.study_planner = StudyPlannerService()
        self.voice = VoiceTutorService(tutor)

    def sync_learning_context(self, student_id, name, course, language=None, learning_preference=None):
        existing = self.tutor.get_student_profile(student_id)
        if existing is not None:
            effective_lang = language if language is not None else existing.student.preferred_language
            effective_pref = learning_preference if learning_preference is not None else existing.student.learning_preference
        else:
            effective_lang = language or 'en'
            effective_pref = learning_preference or 'step-by-step'
        return self.tutor.create_or_load_student(student_id, name, course, effective_lang, effective_pref)

    def ask_tutor(self, student_id, course_id, text, language=None, document_ids: Iterable[str] | None = None, session_id='host-app', chat_history=None):
        if language is None:
            p = self.tutor.get_student_profile(student_id)
            if p and p.student and p.student.preferred_language:
                language = p.student.preferred_language
        return self.tutor.ask(StudentQuery(
            student_id=student_id,
            session_id=session_id,
            text=text,
            course=course_id,
            preferred_language=language,
            document_ids=list(document_ids) if document_ids is not None else None,
            chat_history=chat_history,
        ))

    def create_diagnostic(self, student_id, topic, language='en', document_ids=None):
        p = self.tutor.get_student_profile(student_id)
        topic = topic.strip()
        if not topic:
            raise ValueError('Diagnostic topic cannot be empty')
        concepts = list(p.weak_concepts[:3]) if p and p.weak_concepts else []
        a = self.tutor.qa._heuristic(topic)
        concepts.extend(a.concepts)
        concepts.extend(a.prerequisites[:2])
        concepts = [x for x in dict.fromkeys(concepts) if x] or [topic]
        return self.tutor.create_assessment(
            student_id,
            topic,
            concepts[:5],
            language,
            document_ids=list(document_ids or []) if document_ids is not None else None,
        )

    def submit_diagnostic(self, student_id, assessment, answers, language='en'):
        result = self.tutor.submit_assessment(student_id, assessment, answers, language)
        # Update spaced repetition and study plan after assessment submission
        p = self.tutor.get_student_profile(student_id)
        if p:
            self.spaced_repetition.update_queue(p)
            self.study_planner.build_study_plan(p)
            self.tutor.store.save(p)
        return result

    def get_learning_profile(self, student_id):
        p = self.tutor.get_student_profile(student_id)
        if p:
            self.spaced_repetition.update_queue(p)
            self.study_planner.build_study_plan(p)
        return p

    def get_content_creation_context(self, student_id):
        p = self.tutor.get_student_profile(student_id)
        if not p:
            raise ValueError('Student profile does not exist')
        return build_content_creation_context(p)

    def get_next_learning_action(self, student_id):
        p = self.tutor.get_student_profile(student_id)
        if not p:
            raise ValueError('Student profile does not exist')
        return self.tutor.learning_orchestrator.next_action(p)

    def upload_course_material(self, student_id, file_path, filename, course='General'):
        return self.tutor.upload_document(student_id, file_path, filename, course=course)

    def list_course_materials(self, student_id, course=None):
        return self.tutor.ingestion.list_documents(student_id, 'student_upload', course=course)

    def generate_learning_resources(self, student_id, topic, kinds, language='en', document_ids=None):
        return self.tutor.generate_content(student_id, topic, kinds, language, document_ids=document_ids)

    def ask_voice_tutor(self, student_id, course_id, audio_data, document_ids=None, language=None, session_id='voice-session'):
        return self.voice.ask_voice(
            student_id=student_id,
            audio_data=audio_data,
            course_id=course_id,
            document_ids=list(document_ids or []),
            language=language,
            session_id=session_id,
        )

    def get_study_plan(self, student_id):
        p = self.tutor.get_student_profile(student_id)
        if not p:
            return []
        return self.study_planner.build_study_plan(p)

    def get_review_queue(self, student_id):
        p = self.tutor.get_student_profile(student_id)
        if not p:
            return []
        return self.spaced_repetition.update_queue(p)

    def record_concept_review(self, student_id, concept: str, remembered: bool):
        p = self.tutor.get_student_profile(student_id)
        if not p:
            raise ValueError('Student profile does not exist')
        res = self.spaced_repetition.record_review(p, concept, remembered)
        self.study_planner.build_study_plan(p)
        self.tutor.store.save(p)
        return res

    def cleanup_audio(self):
        return self.voice.cleanup_session_audio()

    def get_supported_capabilities(self):
        return self.tutor.supported_capabilities()

    def health(self):
        return self.tutor.health()

def build_module(data_dir=None, test_mode=False):
    return LearningIntelligenceModule(build_system(data_dir=data_dir, test_mode=test_mode))
