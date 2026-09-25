from src.integration import build_module


def test_host_facade_learning_context_and_profile(tmp_path):
    module=build_module(str(tmp_path),test_mode=True)
    p=module.sync_learning_context('host-1','Host Student','Artificial Intelligence','en','step-by-step')
    assert p.student.student_id=='host-1'
    loaded=module.get_learning_profile('host-1')
    assert loaded.student.course=='Artificial Intelligence'


def test_host_facade_material_listing(tmp_path):
    module=build_module(str(tmp_path),test_mode=True)
    module.sync_learning_context('host-2','Host Student','Computer Science')
    f=tmp_path/'notes.txt'; f.write_text('CNN filters learn local visual features. Pooling can reduce spatial dimensions.',encoding='utf-8')
    meta=module.upload_course_material('host-2',str(f),'notes.txt')
    listed=module.list_course_materials('host-2')
    assert [x.document_id for x in listed]==[meta.document_id]