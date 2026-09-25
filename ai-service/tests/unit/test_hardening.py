import pytest
from pathlib import Path
from src.language.service import LanguageService
from src.query_analysis.service import QueryAnalyzer
from src.validation.service import Validator
from infrastructure.storage.json_store import JsonProfileStore
from src.contracts.models import Student,StudentProfile,Evidence
from infrastructure.document_loaders.loaders import safe_name
from src.core.exceptions import DocumentError

def test_student_id_path_traversal_blocked(tmp_path):
    store=JsonProfileStore(tmp_path)
    with pytest.raises(ValueError): store.load('../escape')

def test_atomic_profile_roundtrip(tmp_path):
    store=JsonProfileStore(tmp_path); p=StudentProfile(student=Student(student_id='s-1',name='Learner'))
    p.concept_mastery['CNN']=.7; store.save(p); assert store.load('s-1').concept_mastery['CNN']==.7

def test_unsafe_filename_blocked():
    with pytest.raises(DocumentError): safe_name('../secret.pdf')
    with pytest.raises(DocumentError): safe_name('malware.exe')

def test_language_direction_and_script():
    s=LanguageService(); ar=s.detect('اشرح CNN'); am=s.detect('እባክዎ CNN አስረዳ')
    assert ar.direction=='rtl' and ar.script=='Arabic'; assert am.direction=='ltr' and am.script=='Ethiopic'

def test_query_unknown_topic_remains_structured():
    a=QueryAnalyzer().analyze('Explain Kubernetes scheduling with a diagram')
    assert a.topic and a.retrieval_required and 'diagram' in a.requested_outputs

def test_confidence_rewards_strong_evidence():
    v=Validator(); strong=[Evidence(chunk_id='1',text='x',source='u',score=.9,authority='official_documentation',trust_score=.99)]
    weak=[Evidence(chunk_id='2',text='x',source='u',score=.1,authority='unverified',trust_score=.2)]
    assert v.confidence(strong)>v.confidence(weak); assert v.sufficient(strong); assert not v.sufficient(weak)