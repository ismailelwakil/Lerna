from __future__ import annotations

import pytest
from app.ui_i18n import (
    UI_CATALOG,
    PHASE_1_KEYS,
    t,
    get_style_display,
    get_mode_display,
    extract_placeholders,
)

SUPPORTED_10 = ["en", "ar", "fr", "sw", "ha", "am", "so", "yo", "ig", "zu"]


def test_english_phase1_labels():
    """1. English Phase-1 labels return expected values."""
    assert t("tab_tutor", "en") == "Tutor"
    assert t("tab_my_learning", "en") == "My Learning"
    assert t("tab_course_materials", "en") == "Course Materials"
    assert t("tab_study_tools", "en") == "Study Tools"
    assert t("save_preferences", "en") == "Save preferences"
    assert t("sources_used", "en") == "Sources used"
    assert t("available_materials", "en") == "Available materials"
    assert t("status_ready", "en") == "Ready"


def test_arabic_phase1_labels():
    """2. Arabic Phase-1 labels return expected values."""
    assert t("tab_tutor", "ar") == "المعلم"
    assert t("tab_my_learning", "ar") == "تعلمي"
    assert t("tab_course_materials", "ar") == "مواد المقرر"
    assert t("tab_study_tools", "ar") == "أدوات الدراسة"
    assert t("save_preferences", "ar") == "حفظ التفضيلات"
    assert t("sources_used", "ar") == "المصادر المستخدمة"
    assert t("status_ready", "ar") == "جاهز"


def test_french_phase1_labels():
    """3. French Phase-1 labels return expected values."""
    assert t("tab_tutor", "fr") == "Tuteur"
    assert t("tab_my_learning", "fr") == "Mon apprentissage"
    assert t("tab_course_materials", "fr") == "Supports de cours"
    assert t("tab_study_tools", "fr") == "Outils d'étude"
    assert t("save_preferences", "fr") == "Enregistrer les préférences"
    assert t("sources_used", "fr") == "Sources utilisées"
    assert t("status_ready", "fr") == "Prêt"


def test_hausa_phase1_labels():
    """4. Hausa Phase-1 labels return expected values."""
    assert t("tab_tutor", "ha") == "Malami"
    assert t("tab_my_learning", "ha") == "Koyona"
    assert t("tab_course_materials", "ha") == "Kayan Karatu"
    assert t("tab_study_tools", "ha") == "Kayan Nazari"
    assert t("save_preferences", "ha") == "Ajiye zaɓuɓɓuka"
    assert t("sources_used", "ha") == "Hanyoyin da aka yi amfani da su"
    assert t("status_ready", "ha") == "A shirye"


def test_isizulu_phase1_labels():
    """5. isiZulu Phase-1 labels return expected values."""
    assert t("tab_tutor", "zu") == "Uthisha"
    assert t("tab_my_learning", "zu") == "Ukufunda Kwami"
    assert t("tab_course_materials", "zu") == "Izinto Zesifundo"
    assert t("tab_study_tools", "zu") == "Amathuluzi Okufunda"
    assert t("save_preferences", "zu") == "Gcina izintandokazi"
    assert t("sources_used", "zu") == "Imithombo esetshenzisiwe"
    assert t("status_ready", "zu") == "Kumi ngomumo"


def test_yoruba_phase1_labels():
    """6. Yoruba Phase-1 labels return expected values."""
    assert t("tab_tutor", "yo") == "Olùkọ́"
    assert t("tab_my_learning", "yo") == "Ẹ̀kọ́ Mi"
    assert t("tab_course_materials", "yo") == "Àwọn Ohun-èkọ́"
    assert t("tab_study_tools", "yo") == "Àwọn Ohun Èlò Ìkẹ́kọ̀ọ́"
    assert t("save_preferences", "yo") == "Fi àwọn ìfẹ́ràn pamọ́"
    assert t("sources_used", "yo") == "Àwọn orísun tí a lò"
    assert t("status_ready", "yo") == "Ó ti wà ní sẹpẹ́"


def test_igbo_phase1_labels():
    """7. Igbo Phase-1 labels return expected values."""
    assert t("tab_tutor", "ig") == "Onye Nkụzi"
    assert t("tab_my_learning", "ig") == "Mmụta M"
    assert t("tab_course_materials", "ig") == "Ngwa Ọmụmụ"
    assert t("tab_study_tools", "ig") == "Ngwaọrụ Ọmụmụ"
    assert t("save_preferences", "ig") == "Chekwaa mmasị"
    assert t("sources_used", "ig") == "Isi mmalite e ji mee ihe"
    assert t("status_ready", "ig") == "Dị njikere"


def test_kiswahili_phase1_labels():
    """8. Kiswahili Phase-1 labels return expected values."""
    assert t("tab_tutor", "sw") == "Mkufunzi"
    assert t("tab_my_learning", "sw") == "Kujifunza Kwangu"
    assert t("tab_course_materials", "sw") == "Nyenzo za Kozi"
    assert t("tab_study_tools", "sw") == "Zana za Masomo"
    assert t("save_preferences", "sw") == "Hifadhi mapendeleo"
    assert t("sources_used", "sw") == "Vyanzo vilivyotumika"
    assert t("status_ready", "sw") == "Tayari"


def test_amharic_phase1_labels():
    """9. Amharic Phase-1 labels return expected values."""
    assert t("tab_tutor", "am") == "አስተማሪ"
    assert t("tab_my_learning", "am") == "ትምህርቴ"
    assert t("tab_course_materials", "am") == "የትምህርት ቁሳቁሶች"
    assert t("tab_study_tools", "am") == "የጥናት መሣሪያዎች"
    assert t("save_preferences", "am") == "ምርጫዎችን አስቀምጥ"
    assert t("sources_used", "am") == "ጥቅም ላይ የዋሉ ምንጮች"
    assert t("status_ready", "am") == "ዝግጁ"


def test_somali_phase1_labels():
    """10. Somali Phase-1 labels return expected values."""
    assert t("tab_tutor", "so") == "Macallinka"
    assert t("tab_my_learning", "so") == "Waxbarashadayda"
    assert t("tab_course_materials", "so") == "Agabka Koorsada"
    assert t("tab_study_tools", "so") == "Qalabka Waxbarashada"
    assert t("save_preferences", "so") == "Keydi xulashooyinka"
    assert t("sources_used", "so") == "Ilaha la adeegsaday"
    assert t("status_ready", "so") == "Diyaar"


def test_all_phase1_keys_exist_in_all_ten_languages():
    """11. Completeness: All Phase-1 keys exist in ALL 10 supported languages."""
    for lang in SUPPORTED_10:
        assert lang in UI_CATALOG, f"Missing language catalog: {lang}"
        catalog = UI_CATALOG[lang]
        for key in PHASE_1_KEYS:
            assert key in catalog, f"Language '{lang}' is missing required key '{key}'"
            assert isinstance(catalog[key], str) and catalog[key].strip(), f"Empty value for '{key}' in '{lang}'"


def test_unknown_language_falls_back_safely_to_english():
    """12. Defensive safety: Unrecognized language code falls back to English."""
    assert t("tab_tutor", "xx") == "Tutor"
    assert t("save_preferences", "unsupported_code") == "Save preferences"
    assert t("sources_used", None) == "Sources used"


def test_unknown_or_missing_key_does_not_crash():
    """13. Defensive safety: Non-existent key returns key name without raising KeyError."""
    assert t("non_existent_key_123", "en") == "non_existent_key_123"
    assert t("another_missing_key", "ar") == "another_missing_key"


def test_placeholder_sets_match_english_across_every_dynamic_key():
    """14. Placeholder parity: All dynamic keys preserve identical placeholder tokens."""
    for key in PHASE_1_KEYS:
        en_template = UI_CATALOG["en"][key]
        en_placeholders = extract_placeholders(en_template)
        if not en_placeholders:
            continue
        for lang in SUPPORTED_10:
            if lang == "en":
                continue
            lang_template = UI_CATALOG[lang][key]
            lang_placeholders = extract_placeholders(lang_template)
            assert lang_placeholders == en_placeholders, (
                f"Placeholder mismatch for key '{key}' in '{lang}': "
                f"expected {en_placeholders}, got {lang_placeholders}"
            )


def test_learning_preference_preserves_backend_slugs():
    """15. Learning preference display labels localize while preserving backend slugs."""
    slugs = ["step-by-step", "socratic", "visual", "analogy-first", "code-first"]
    for slug in slugs:
        # English
        en_label = get_style_display(slug, "en")
        assert en_label in ["Step-by-step", "Socratic", "Visual", "Analogy-first", "Code-first"]

        # Arabic
        ar_label = get_style_display(slug, "ar")
        assert ar_label != slug
        assert isinstance(ar_label, str) and len(ar_label) > 0

        # French
        fr_label = get_style_display(slug, "fr")
        assert fr_label != slug

    # Unrecognized slug formats gracefully
    assert get_style_display("custom-style", "en") == "Custom Style"


def test_tutoring_style_preserves_internal_values():
    """16. Tutoring style displays localize while internal values remain unchanged."""
    modes = ["Direct Explanation", "Socratic Guidance"]
    for mode in modes:
        en_val = get_mode_display(mode, "en")
        assert en_val == mode

        ar_val = get_mode_display(mode, "ar")
        assert ar_val != mode
        assert isinstance(ar_val, str)

        fr_val = get_mode_display(mode, "fr")
        assert fr_val != mode


def test_sources_used_localizes_across_all_ten_languages():
    """17. 'sources_used' title is distinctly localized in all 10 supported languages."""
    seen_titles = {}
    for lang in SUPPORTED_10:
        val = t("sources_used", lang)
        assert isinstance(val, str) and len(val.strip()) > 0
        seen_titles[lang] = val

    # Verify key target languages have their expected translations
    assert seen_titles["en"] == "Sources used"
    assert seen_titles["ar"] == "المصادر المستخدمة"
    assert seen_titles["fr"] == "Sources utilisées"
    assert seen_titles["ha"] == "Hanyoyin da aka yi amfani da su"
    assert seen_titles["zu"] == "Imithombo esetshenzisiwe"


def test_filename_and_citations_untransformed():
    """18. Filename, page numbers, and citation payloads format correctly without corruption."""
    formatted_page = t("page_indicator", "en", page=3)
    assert formatted_page == " · page 3"

    formatted_page_ar = t("page_indicator", "ar", page=5)
    assert "5" in formatted_page_ar

    notification_en = t("material_ready_notification", "en", filename="lecture_1.txt")
    assert notification_en == "lecture_1.txt is ready for AI Tutor."

    notification_fr = t("material_ready_notification", "fr", filename="lecture_1.txt")
    assert "lecture_1.txt" in notification_fr
