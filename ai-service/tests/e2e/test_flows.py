from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery
def q(ai,text,docs=[]): return ai.ask(StudentQuery(student_id='s',session_id='x',text=text,document_ids=docs))
def test_english_grounded(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); r=q(ai,'Explain CNN'); assert r.language.language=='en' and r.evidence and not r.abstained
def test_arabic_roundtrip(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); r=q(ai,'اشرحلي CNN'); assert r.language.language=='ar' and 'شرح' in r.answer
def test_assessment_profile(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); a=ai.create_assessment('s','CNN',['filters']); res=ai.submit_assessment('s',a,{a.questions[0].question_id:a.questions[0].expected}); assert res.score==1 and ai.get_student_profile('s').concept_mastery['filters']==1
def test_personalized_gap(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); p=ai.create_or_load_student('s','S'); p.prerequisite_gaps=['matrices']; ai.store.save(p); r=q(ai,'Explain CNN'); assert 'prerequisite-remediation' in r.answer
def test_mixed_routing_synthesis(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); r=q(ai,'Explain CNN code quiz summary'); assert len(r.routing)>=4 and '```python' in r.answer and 'grounded explanation' in r.answer.lower()
def test_insufficient_abstains(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); r=q(ai,'Explain totallyunknownquantumtopicxyz'); assert r.abstained
def test_conflict_detection(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); f=tmp_path/'c.md'; f.write_text('This method always uses pooling. Another statement says it never uses pooling.',encoding='utf-8'); m=ai.upload_document('s',f,'c.md'); r=q(ai,'pooling',[m.document_id]); assert r.conflict_detected
def test_facade_smoke(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); p=ai.create_or_load_student('s','S'); assert p.student.student_id=='s' and ai.health()['provider_mode']=='MOCK'
def test_persistence_restart(tmp_path):
 ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); q(ai,'Explain CNN'); ai2=build_system(str(tmp_path),test_mode=True); assert ai2.get_student_profile('s').learning_history