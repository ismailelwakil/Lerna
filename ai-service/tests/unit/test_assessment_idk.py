from src.assessment.service import AssessmentService, idk_label
from src.contracts.models import Assessment, AssessmentQuestion

def test_mcq_always_has_i_dont_know_option():
    a=AssessmentService().generate('CNN',['pooling'],'en',None)
    assert any(idk_label('en') in q.options for q in a.questions if q.kind in ('mcq','true_false'))

def test_i_dont_know_is_not_misconception():
    q=AssessmentQuestion(question_id='q',concept='pooling',kind='short',prompt='What is pooling?',expected='Pooling reduces spatial dimensions.')
    a=Assessment(assessment_id='a',topic='CNN',questions=[q])
    r=AssessmentService().analyze(a,{'q':"I don't know"})
    assert r.score==0
    assert r.misconceptions==[]
    assert r.unknown_concepts==['pooling']