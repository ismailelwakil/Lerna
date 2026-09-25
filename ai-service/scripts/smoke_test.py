import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery
with tempfile.TemporaryDirectory() as d:
    ai=build_system(d,test_mode=True); ai.create_or_load_student('s1','Malak','AI','en');
    p=Path(d)/'course.md'; p.write_text('CNN convolution filters pooling are used for spatial feature learning.',encoding='utf-8'); meta=ai.upload_document('s1',p,'course.md')
    r=ai.ask(StudentQuery(student_id='s1',session_id='smoke',text='Explain CNN and give code quiz summary',document_ids=[meta.document_id])); a=ai.create_assessment('s1','CNN',['convolution','filters']); answers={q.question_id:q.expected for q in a.questions}; ar=ai.submit_assessment('s1',a,answers); content,_=ai.generate_content('s1','CNN',['summary','diagram']); profile=ai.get_student_profile('s1'); assert r.answer and ar.score==1 and profile.assessment_history and content; print('SMOKE TEST PASSED')