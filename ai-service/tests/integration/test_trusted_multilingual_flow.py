from src.integration.service import build_module

def test_general_question_uses_trusted_external_not_uploaded_material(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    m.sync_learning_context('s','Student','AI')
    f=tmp_path/'cnn.txt'; f.write_text('CNN-only local fact: EduKernel-X91.',encoding='utf-8')
    m.upload_course_material('s',str(f),'cnn.txt')
    r=m.ask_tutor('s','AI','Explain quantum teleportation simply.')
    assert not r.abstained
    assert r.knowledge_source=='trusted_external'
    assert r.trusted_search_state=='ready'
    assert r.evidence
    assert all(e.source_type=='trusted_external' for e in r.evidence)
    assert all('cnn.txt' not in e.source for e in r.evidence)
    assert any('quantum' in e.text.lower() for e in r.evidence)

def test_source_constrained_never_uses_external_fallback(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    m.sync_learning_context('s','Student','AI')
    f=tmp_path/'cnn.txt'; f.write_text('CNN uses convolution and pooling.',encoding='utf-8')
    meta=m.upload_course_material('s',str(f),'cnn.txt')
    r=m.ask_tutor('s','AI','According to my uploaded course material, explain quantum teleportation.',document_ids=[meta.document_id])
    assert r.abstained
    assert r.knowledge_source=='uploaded_material'
    assert r.trusted_search_state=='not_required'
    assert all(e.source_type=='student_upload' for e in r.evidence)

def test_arabic_query_preserves_original_and_normalizes_internal_query(tmp_path):
    m=build_module(str(tmp_path),test_mode=True)
    m.sync_learning_context('s','Student','AI','ar')
    r=m.ask_tutor('s','AI','ممكن تشرحلي CNN ببساطة؟')
    assert r.language.language=='ar'
    assert r.language.original_text=='ممكن تشرحلي CNN ببساطة؟'
    assert r.language.normalized_english_query
    assert 'CNN' in r.language.normalized_english_query
    assert not r.abstained
    assert r.answer.startswith('شرح مخصص:')