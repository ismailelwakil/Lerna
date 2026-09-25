from src.orchestration.factory import build_system
from src.contracts.models import StudentQuery

def test_lexical_and_semantic_hybrid_metadata(tmp_path):
    ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S')
    f=tmp_path/'course.md'; f.write_text('Gradient descent updates parameters using the gradient.\n\nBackpropagation computes gradients with the chain rule.',encoding='utf-8')
    m=ai.upload_document('s',f,'course.md'); ev,_=ai.retrieval.retrieve('chain rule gradient','s',[m.document_id],'backpropagation')
    assert ev and ev[0].retrieval_method=='hybrid-semantic-bm25-rrf' and ev[0].page==1

def test_upload_deduplicates_by_hash(tmp_path):
    ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S'); f=tmp_path/'x.md'; f.write_text('CNN filters',encoding='utf-8')
    a=ai.upload_document('s',f,'x.md'); b=ai.upload_document('s',f,'x.md'); assert a.document_id==b.document_id