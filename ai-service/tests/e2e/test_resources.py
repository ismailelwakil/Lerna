from pathlib import Path
from src.orchestration.factory import build_system

def test_real_local_artifacts_created_in_test_mode(tmp_path):
    ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S')
    f=tmp_path/'c.md'; f.write_text('CNN uses convolution filters for spatial feature extraction.',encoding='utf-8'); ai.upload_document('s',f,'c.md')
    out,_=ai.generate_content('s','CNN',['diagram','presentation'],'en')
    assert Path(out['diagram']['path']).exists() and out['diagram']['path'].endswith('.svg')
    assert Path(out['presentation']['path']).exists() and out['presentation']['path'].endswith('.pptx')

def test_multimedia_unavailable_is_explicit(tmp_path):
    ai=build_system(str(tmp_path),test_mode=True); ai.create_or_load_student('s','S')
    out,_=ai.generate_content('s','CNN',['image','audio'],'en')
    assert out['image']['type']=='unavailable' and out['audio']['type']=='unavailable'