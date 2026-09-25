from src.assessment.service import AssessmentService
from src.contracts.models import Assessment, AssessmentQuestion
from src.content_context import build_content_creation_context
from src.integration.service import build_module

def test_pooling_contradiction_is_wrong_and_misconception_detected():
    q=AssessmentQuestion(question_id='q1',concept='pooling',kind='short',prompt='Explain pooling',expected='Pooling downsamples or reduces the spatial dimensions of feature maps, commonly using max or average pooling, reducing computation.')
    a=Assessment(assessment_id='a1',topic='CNN',questions=[q])
    r=AssessmentService().analyze(a,{'q1':'Pooling increases the spatial dimensions of feature maps.'})
    assert r.score==0
    assert 'pooling' in r.weak_concepts
    assert r.misconceptions

def test_empty_assessment_is_rejected():
    a=Assessment(assessment_id='a',topic='CNN',questions=[])
    try:AssessmentService().analyze(a,{})
    except ValueError:return
    raise AssertionError('empty assessment should fail')

def test_profile_adapter_and_next_action(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    p=m.sync_learning_context('student1','Student','CNN','en','visual')
    p.concept_mastery={'pooling':.3,'filters':.9}; p.weak_concepts=['pooling']; p.strengths=['filters']; m.tutor.store.save(p)
    ctx=m.get_content_creation_context('student1'); action=m.get_next_learning_action('student1')
    assert ctx.weak_areas==['pooling']
    assert ctx.concept_mastery['filters']==.9
    assert 'pooling' in action.target_concepts

def test_personalized_content_tracks_learner_snapshot(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    p=m.sync_learning_context('student1','Student','CNN')
    p.concept_mastery={'pooling':.2}; p.weak_concepts=['pooling']; m.tutor.store.save(p)
    out,_=m.generate_learning_resources('student1','CNN',['summary'])
    saved=m.get_learning_profile('student1')
    last=saved.generated_resources[-1]
    assert last['target_concepts']==['pooling']
    assert last['learner_snapshot']['weak_areas']==['pooling']
    assert 'summary' in out

def test_source_constrained_irrelevant_evidence_hard_abstains(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    m.sync_learning_context('student1','Student','CNN')
    f=tmp_path/'cnn.txt'; f.write_text('CNN uses convolution filters, ReLU, and pooling for image processing.',encoding='utf-8')
    m.upload_course_material('student1',str(f),'cnn.txt')
    r=m.ask_tutor('student1','CNN','According to my uploaded course material, what quantum teleportation algorithm is used in our laboratory?')
    assert r.abstained is True
    assert 'does not contain enough information' in r.answer
    assert 'quantum teleportation' not in r.answer.lower().replace('this specific question','')

def test_four_answer_cnn_diagnostic_marks_pooling_weak():
    svc=AssessmentService()
    qs=[
      AssessmentQuestion(question_id='q1',concept='convolution',kind='mcq',prompt='q',options=['correct','wrong'],expected='correct'),
      AssessmentQuestion(question_id='q2',concept='filters',kind='short',prompt='q',expected='Filters are learnable kernels that scan local regions and detect features such as edges, textures, and higher-level patterns.'),
      AssessmentQuestion(question_id='q3',concept='pooling',kind='short',prompt='q',expected='Pooling downsamples or reduces the spatial dimensions of feature maps, commonly using max or average pooling, reducing computation.'),
      AssessmentQuestion(question_id='q4',concept='neural networks',kind='short',prompt='q',expected='Neural networks are layered computational models of connected units that learn patterns from data by adjusting weights during training.'),
    ]
    a=Assessment(assessment_id='a',topic='CNN',questions=qs)
    ans={'q1':'wrong','q2':'Filters are learnable kernels that scan local regions to detect edges and textures.','q3':'Pooling increases the spatial dimensions of feature maps.','q4':'Neural networks are computational models made of interconnected layers that learn patterns from data by adjusting weights during training.'}
    r=svc.analyze(a,ans)
    assert r.score==0.5
    assert set(r.weak_concepts)=={'convolution','pooling'}
    assert set(r.strengths)=={'filters','neural networks'}
    assert any('pooling' in x.lower() for x in r.misconceptions)