from pathlib import Path


def test_streamlit_is_student_facing_not_developer_console():
    text = Path('app/streamlit_app.py').read_text(encoding='utf-8')
    forbidden = [
        "Student ID",
        "Load learning context",
        "Developer details",
        "System health",
        "vector_store",
        "embedding_provider",
        "provider_mode",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_streamlit_contains_required_student_features():
    text = Path('app/streamlit_app.py').read_text(encoding='utf-8')
    required = ["AI Tutor", "My Learning", "Course Materials", "Study Tools", "st.chat_input"]
    for phrase in required:
        assert phrase in text