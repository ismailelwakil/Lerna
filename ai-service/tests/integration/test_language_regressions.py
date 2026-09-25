import pytest
from src.contracts.models import Student, StudentQuery, ChatTurn, SUPPORTED_LANGUAGES
from src.integration.service import build_module
from src.language.service import LanguageService, LANGUAGE_NAMES
from src.orchestration.factory import build_system


def test_preference_persistence_survives_resync(tmp_path):
    """BUG-LANG-01: Saved language preference survives app resync/rerun."""
    m = build_module(str(tmp_path), test_mode=True)
    
    # 1. First initialization with Arabic preference
    p = m.sync_learning_context("student-001", "Alex Chen", "Algorithms", language="ar")
    assert p.student.preferred_language == "ar"

    # 2. Re-sync without specifying language (default / rerun simulation)
    p2 = m.sync_learning_context("student-001", "Alex Chen", "Algorithms")
    assert p2.student.preferred_language == "ar", "Saved preference must not be overwritten by demo default 'en'"

    # 3. Direct load from profile store
    stored = m.tutor.get_student_profile("student-001")
    assert stored is not None
    assert stored.student.preferred_language == "ar"


def test_ask_tutor_applies_saved_preferred_language_to_english_query(tmp_path):
    """BUG-LANG-01: English query answered in student's saved preferred language."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-001", "Alex Chen", "Algorithms", language="ar")

    # Ask in English without passing language parameter
    resp = m.ask_tutor("student-001", "Algorithms", "Explain CNN")
    assert resp.answer.startswith("شرح مخصص:"), "Answer must be translated to student's preferred language (Arabic)"
    assert not resp.abstained


def test_french_preference_controls_english_query(tmp_path):
    """BUG-LANG-01: French preference + English query -> French response."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-fr", "Marie Curie", "Computer Science", language="fr")

    resp = m.ask_tutor("student-fr", "Computer Science", "Explain binary search")
    assert resp.answer.startswith("Explication personnalisée : "), "Answer must be translated to student's preferred language (French)"


def test_explicit_per_turn_override_takes_precedence(tmp_path):
    """BUG-LANG-01 & BUG-LANG-02: Explicit per-turn directive overrides saved preference."""
    m = build_module(str(tmp_path), test_mode=True)
    
    # Arabic saved preference, but turn explicitly asks for French
    m.sync_learning_context("student-ar", "Omar", "Algorithms", language="ar")
    resp_fr = m.ask_tutor("student-ar", "Algorithms", "Explain CNN. Answer in French.")
    assert resp_fr.answer.startswith("Explication personnalisée : "), "Explicit 'Answer in French' must override Arabic preference"

    # French saved preference, but turn explicitly asks for Arabic
    m.sync_learning_context("student-fr", "Marie", "Algorithms", language="fr")
    resp_ar = m.ask_tutor("student-fr", "Algorithms", "اشرح بالعربي CNN")
    assert resp_ar.answer.startswith("شرح مخصص:"), "Explicit Arabic request must override French preference"

    # Saved preference is Arabic, but turn explicitly asks for Hausa
    resp_ha = m.ask_tutor("student-ar", "Algorithms", "Explain CNN da hausa")
    assert resp_ha.answer.startswith("Bayani na musamman: "), "Explicit Hausa request must override Arabic preference"


def test_african_language_detection_deterministic():
    """BUG-LANG-02: Morphological markers and function words detect African languages."""
    lang_svc = LanguageService()

    # Hausa queries
    hausa_queries = [
        "Wane sharadi ne dole a cika kafin ayi amfani da binary search?",
        "Don Allah bayyana CNN",
        "Bayyana binary search a saukake",
        "Menene aikin convolution a cikin CNN?",
    ]
    for q in hausa_queries:
        res = lang_svc.detect(q)
        assert res.language == "ha", f"Expected 'ha' for '{q}', got '{res.language}'"

    # isiZulu queries
    zulu_queries = [
        "Ungachaza ukuthi yisiphi isidingo esibalulekile ngaphambi kokusebenzisa i-binary search?",
        "Ngicela chaza CNN",
        "Yini i-binary search futhi isebenza kanjani?",
        "Ngitshele kabanzi ngale ndlela yokusebenzisa amakhodi",
    ]
    for q in zulu_queries:
        res = lang_svc.detect(q)
        assert res.language == "zu", f"Expected 'zu' for '{q}', got '{res.language}'"

    # Kiswahili queries
    swahili_queries = [
        "Tafadhali eleza CNN",
        "Ni nini sharti muhimu kabla ya kutumia binary search?",
    ]
    for q in swahili_queries:
        res = lang_svc.detect(q)
        assert res.language == "sw", f"Expected 'sw' for '{q}', got '{res.language}'"

    # Somali queries
    somali_queries = [
        "Fadlan sharax CNN",
        "Waa maxay shuruudda muhiimka ah ka hor isticmaalka binary search?",
    ]
    for q in somali_queries:
        res = lang_svc.detect(q)
        assert res.language == "so", f"Expected 'so' for '{q}', got '{res.language}'"

    # Yoruba queries
    yoruba_queries = [
        "Jọ̀wọ́ ṣàlàyé CNN",
        "Kí ni àwọn nǹkan pataki ṣaaju ki a to lo binary search?",
    ]
    for q in yoruba_queries:
        res = lang_svc.detect(q)
        assert res.language == "yo", f"Expected 'yo' for '{q}', got '{res.language}'"

    # Igbo queries
    igbo_queries = [
        "Biko kọwaa CNN",
        "Gịnị bụ ihe dị mkpa tupu e jiri binary search?",
    ]
    for q in igbo_queries:
        res = lang_svc.detect(q)
        assert res.language == "ig", f"Expected 'ig' for '{q}', got '{res.language}'"


def test_saved_preferred_language_as_detection_prior():
    """BUG-LANG-02: Saved preferred language breaks ties and guides disambiguation."""
    lang_svc = LanguageService()

    # Short query with ambiguous/sparse Latin words, with Hausa prior
    res_ha = lang_svc.detect("binary search algorithm", preferred_language="ha")
    # Pure English markers trigger 'en'
    assert lang_svc.detect("Explain binary search", preferred_language="ha").language == "en"

    # But with a Hausa marker + English words, Hausa prior boosts ha
    res_ha_marker = lang_svc.detect("wane algorithm ne binary search", preferred_language="ha")
    assert res_ha_marker.language == "ha"

    # Zulu prior boost
    res_zu_marker = lang_svc.detect("chaza binary search algorithm", preferred_language="zu")
    assert res_zu_marker.language == "zu"


def test_translation_prompts_use_explicit_human_readable_names():
    """BUG-LANG-02: Target language in translation system prompt must be full name."""
    lang_svc = LanguageService()

    prompt_ha = lang_svc._translation_system_prompt("en", "ha", ["CNN"])
    assert "Target language: Hausa" in prompt_ha
    assert "Natural prose must be in Hausa" in prompt_ha

    prompt_zu = lang_svc._translation_system_prompt("en", "zu", ["binary search"])
    assert "Target language: isiZulu" in prompt_zu
    assert "Natural prose must be in isiZulu" in prompt_zu

    prompt_sw = lang_svc._translation_system_prompt("en", "sw", [])
    assert "Target language: Kiswahili" in prompt_sw

    prompt_so = lang_svc._translation_system_prompt("en", "so", [])
    assert "Target language: Somali" in prompt_so

    prompt_yo = lang_svc._translation_system_prompt("en", "yo", [])
    assert "Target language: Yoruba" in prompt_yo

    prompt_ig = lang_svc._translation_system_prompt("en", "ig", [])
    assert "Target language: Igbo" in prompt_ig

    prompt_am = lang_svc._translation_system_prompt("en", "am", [])
    assert "Target language: Amharic" in prompt_am


def test_code_switching_honors_input_language(tmp_path):
    """Natural code-switching: Arabic query with English preference still gets Arabic answer."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-en", "Student", "AI", language="en")

    # Arabic question
    resp = m.ask_tutor("student-en", "AI", "ممكن تشرحلي CNN ببساطة؟")
    assert resp.answer.startswith("شرح مخصص:"), "Arabic question should be answered in Arabic even if student preference is English"


def test_english_condition_homograph_detects_english():
    """Test 1: English query containing homograph 'condition' detects as English."""
    lang_svc = LanguageService()
    query = "What condition must be satisfied before using Binary Search?"
    res = lang_svc.detect(query, preferred_language="en")
    assert res.language == "en", f"Expected 'en', got '{res.language}'"


def test_english_condition_query_saved_preference_generates_english(tmp_path):
    """Test 2: Tutor end-to-end with saved English preference yields English answer without French translation."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-homograph-en", "Alex", "Algorithms", language="en")

    query = "What condition must be satisfied before using Binary Search?"
    resp = m.ask_tutor("student-homograph-en", "Algorithms", query)
    assert not resp.abstained
    assert resp.language.language == "en"
    assert not resp.answer.startswith("Explication personnalisée :")
    assert not resp.answer.startswith("Avant d'utiliser")
    assert "binary search" in resp.answer.lower()


def test_genuine_french_condition_query_detects_french():
    """Test 3: Genuine French query containing 'la condition' detects as French."""
    lang_svc = LanguageService()
    query = "Quelle est la condition indispensable avant d'utiliser la recherche binaire ?"
    res = lang_svc.detect(query, preferred_language="fr")
    assert res.language == "fr", f"Expected 'fr', got '{res.language}'"


def test_french_preference_two_simple_points_generates_french(tmp_path):
    """Test 4: Saved French preference generates French response for English two-point query."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-fr-pref2", "Marie", "Algorithms", language="fr")

    query = "Explain in two simple points why binary search requires sorted data."
    resp = m.ask_tutor("student-fr-pref2", "Algorithms", query)
    assert not resp.abstained
    assert resp.answer.startswith("Explication personnalisée : ")


def test_turn2_analogy_query_detects_english_not_yoruba():
    """Turn 2 regression: 'analogy' must not trigger Yoruba 'lo' marker."""
    lang_svc = LanguageService()
    query = "Explain that again using a simple real-world analogy."
    res = lang_svc.detect(query, preferred_language="en")
    assert res.language == "en", f"Expected 'en', got '{res.language}'"
    assert res.language != "yo"


def test_yoruba_marker_still_works_as_real_token():
    """Boundary-aware matching preserves genuine Yoruba token detection."""
    lang_svc = LanguageService()
    query = "Jọ̀wọ́ lo binary search fun alaye"
    res = lang_svc.detect(query)
    assert res.language == "yo", f"Expected 'yo' for genuine Yoruba query, got '{res.language}'"


def test_english_words_containing_short_foreign_markers_detect_english():
    """English words containing substrings of short foreign markers must detect as English."""
    lang_svc = LanguageService()
    cases = [
        ("Explain the analogy clearly.", "analogy contains 'lo'"),
        ("What is the core logic behind it?", "logic contains 'lo'"),
        ("Explain the main concept.", "main contains 'mai'"),
        ("What is the origin of this algorithm?", "origin contains 'orin'"),
        ("Explain the lotus leaf surface effect.", "lotus contains 'otu'"),
    ]
    for text, desc in cases:
        res = lang_svc.detect(text, preferred_language="en")
        assert res.language == "en", f"Failed on '{text}' ({desc}): expected 'en', got '{res.language}'"


def test_turn2_end_to_end_tutor_generates_english_not_yoruba(tmp_path):
    """Tutor Turn 2 query with saved English preference generates English response."""
    m = build_module(str(tmp_path), test_mode=True)
    m.sync_learning_context("student-turn2", "Alex", "Algorithms", language="en")

    # Turn 1
    resp1 = m.ask_tutor("student-turn2", "Algorithms", "What condition must be satisfied before using Binary Search?")
    assert not resp1.abstained
    assert resp1.language.language == "en"

    # Turn 2 with history
    history = [
        ChatTurn(role="user", content="What condition must be satisfied before using Binary Search?"),
        ChatTurn(role="assistant", content=resp1.answer),
    ]
    query = "Explain that again using a simple real-world analogy."
    resp2 = m.ask_tutor("student-turn2", "Algorithms", query, chat_history=history)
    assert not resp2.abstained
    assert resp2.language.language == "en"
    assert not resp2.answer.startswith("Àlàyé àdáni:"), "Turn 2 response must NOT be translated to Yoruba"
    assert not resp2.answer.startswith("Explication personnalisée :")


