from __future__ import annotations
import base64

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src.contracts.models import SUPPORTED_LANGUAGES
from src.core.config import Settings
from src.integration import build_module
from src.assessment.service import idk_label
from app.ui_i18n import t, get_style_display, get_mode_display

LANG_NAMES = {
    "en": "English",
    "ar": "العربية",
    "fr": "Français",
    "sw": "Kiswahili",
    "ha": "Hausa",
    "am": "አማርኛ",
    "so": "Soomaali",
    "yo": "Yorùbá",
    "ig": "Igbo",
    "zu": "isiZulu",
}

TOOL_LABELS = {
    "explanation": "Deep Explanation",
    "summary": "Summary",
    "notes": "Study Notes",
    "study_guide": "Study Guide",
    "flashcards": "Flashcards",
    "quiz": "Practice Quiz",
    "exam": "Formal Exam",
    "practice": "Problem Set",
    "code": "Code Example",
    "coding_exercise": "Coding Exercise",
    "diagram": "Architecture Diagram",
    "presentation": "Presentation Deck",
    "analogy": "Analogy",
    "comparison": "Comparative Table",
    "question_bank": "Question Bank",
}

st.set_page_config(
    page_title="AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "assessment" not in st.session_state:
    st.session_state.assessment = None
if "last_topic" not in st.session_state:
    st.session_state.last_topic = ""
if "generated_outputs" not in st.session_state:
    st.session_state.generated_outputs = {}
if "assessment_result" not in st.session_state:
    st.session_state.assessment_result = None


def inject_theme(dark: bool) -> None:
    if dark:
        palette = {
            "bg": "#071426",
            "bg2": "#0B1D34",
            "surface": "#0F2744",
            "surface2": "#132E4F",
            "surface3": "#18395F",
            "text": "#F5FAFF",
            "muted": "#9DB4CA",
            "border": "#24486E",
            "primary": "#74C5F4",
            "primary2": "#A7DCF8",
            "primary_text": "#071426",
            "success": "#42C88A",
            "warning": "#F1C46A",
            "shadow": "rgba(0,0,0,.24)",
            "chat_user": "#16385E",
            "chat_ai": "#0F2744",
        }
    else:
        palette = {
            "bg": "#F5FBFF",
            "bg2": "#EAF6FD",
            "surface": "#FFFFFF",
            "surface2": "#F3FAFF",
            "surface3": "#E3F3FC",
            "text": "#0A2540",
            "muted": "#61778C",
            "border": "#D5EAF6",
            "primary": "#136FA3",
            "primary2": "#0E5B88",
            "primary_text": "#FFFFFF",
            "success": "#17865B",
            "warning": "#A86708",
            "shadow": "rgba(20,74,110,.08)",
            "chat_user": "#E2F3FD",
            "chat_ai": "#FFFFFF",
        }

    css = f"""
<style>
:root {{
    --bg: {palette['bg']};
    --bg2: {palette['bg2']};
    --surface: {palette['surface']};
    --surface2: {palette['surface2']};
    --surface3: {palette['surface3']};
    --text: {palette['text']};
    --muted: {palette['muted']};
    --border: {palette['border']};
    --primary: {palette['primary']};
    --primary2: {palette['primary2']};
    --primary-text: {palette['primary_text']};
    --success: {palette['success']};
    --warning: {palette['warning']};
    --shadow: {palette['shadow']};
    --chat-user: {palette['chat_user']};
    --chat-ai: {palette['chat_ai']};
}}

html, body, [class*="css"], .stApp {{
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

.stApp {{
    background: var(--bg);
    color: var(--text);
}}

[data-testid="stHeader"] {{
    background: var(--bg);
    border-bottom: 1px solid var(--border);
}}

[data-testid="stSidebar"], [data-testid="collapsedControl"] {{
    display: none !important;
}}

.block-container {{
    max-width: 1240px;
    padding-top: 4.5rem;
    padding-bottom: 3rem;
}}

h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stCaptionContainer"] {{
    color: var(--text) !important;
}}

[data-testid="stCaptionContainer"], .muted {{
    color: var(--muted) !important;
}}

.feature-shell {{
    border: 1px solid var(--border);
    background: var(--surface);
    border-radius: 20px;
    padding: 1rem 1.1rem;
    box-shadow: 0 10px 28px var(--shadow);
}}

.feature-head {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: .85rem;
}}

.feature-title {{
    font-size: 1.7rem;
    font-weight: 750;
    line-height: 1.2;
    color: var(--text);
    margin-bottom: .25rem;
}}

.feature-subtitle {{
    color: var(--muted);
    font-size: .96rem;
}}

.context-line {{
    display: flex;
    flex-wrap: wrap;
    gap: .45rem;
    margin-top: .7rem;
}}

.context-chip {{
    display: inline-flex;
    align-items: center;
    padding: .32rem .68rem;
    border-radius: 999px;
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: .83rem;
}}

.section-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1rem;
    box-shadow: 0 7px 22px var(--shadow);
}}

.metric-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: .95rem 1rem;
    min-height: 104px;
}}
.metric-kicker {{
    font-size: .78rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .05em;
}}
.metric-value {{
    color: var(--text);
    font-size: 1.55rem;
    font-weight: 760;
    margin-top: .18rem;
}}

.source-card {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-left: 3px solid var(--primary);
    border-radius: 12px;
    padding: .72rem .8rem;
    margin: .45rem 0;
    color: var(--text);
}}

.status-ready {{
    color: var(--success);
    font-weight: 650;
}}

[data-baseweb="tab-list"] {{
    gap: .35rem;
    background: var(--surface);
    padding: .33rem;
    border: 1px solid var(--border);
    border-radius: 13px;
    box-shadow: 0 5px 15px var(--shadow);
}}
button[data-baseweb="tab"] {{
    border-radius: 9px;
    color: var(--muted) !important;
    font-weight: 650;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    background: var(--surface3) !important;
    color: var(--text) !important;
}}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {{
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface2) !important;
    color: var(--text) !important;
    font-weight: 650 !important;
    min-height: 2.55rem;
}}
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {{
    background: var(--primary) !important;
    color: var(--primary-text) !important;
    border-color: var(--primary) !important;
}}
.stButton > button:hover,
.stDownloadButton > button:hover {{
    border-color: var(--primary) !important;
}}

[data-testid="stChatMessage"] {{
    border: 1px solid var(--border);
    border-radius: 15px;
    box-shadow: 0 5px 16px var(--shadow);
    margin-bottom: .58rem;
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {{
    background: var(--chat-user);
}}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {{
    background: var(--chat-ai);
}}

[data-testid="stChatInput"] {{
    background: var(--surface) !important;
    border-color: var(--border) !important;
}}

[data-testid="stFileUploader"],
[data-testid="stExpander"],
[data-testid="stForm"] {{
    background: var(--surface);
    border-color: var(--border) !important;
    border-radius: 14px;
}}

[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {{
    background: var(--surface) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
}}

[data-testid="stAlert"] {{
    border-radius: 12px;
}}

hr {{
    border-color: var(--border) !important;
}}

.tool-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 15px;
    padding: .95rem;
    min-height: 104px;
}}
.tool-card strong {{ color: var(--text); }}
.tool-card span {{ color: var(--muted); font-size: .87rem; }}

@media (max-width: 800px) {{
    .block-container {{ padding-left: .75rem; padding-right: .75rem; }}
    .feature-title {{ font-size: 1.45rem; }}
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def clean_markdown(text: str) -> str:
    if not text:
        return ""

    cleaned = re.sub(
        r"\[svg\]\([^)]*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"<svg\b[^>]*>.*?</svg>",
        "",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r"(?im)^\s*svg\s*$",
        "",
        cleaned,
    )

    # Protect fenced code blocks before applying display-only Markdown cleanup.
    code_blocks = []

    def protect_code(match):
        code_blocks.append(
            match.group(0)
        )
        return f"@@CODE_BLOCK_{len(code_blocks) - 1}@@"

    cleaned = re.sub(
        r"```[\s\S]*?```",
        protect_code,
        cleaned,
    )

    # Keep the existing compact heading style outside code blocks only.
    cleaned = re.sub(
        r"(?m)^#{1,6}\s+(.+)$",
        r"**\1**",
        cleaned,
    )

    cleaned = re.sub(
        r"\n{3,}",
        "\n\n",
        cleaned,
    )

    # Restore generated code byte-for-byte so Python comments remain valid.
    for index, block in enumerate(
        code_blocks
    ):
        cleaned = cleaned.replace(
            f"@@CODE_BLOCK_{index}@@",
            block,
        )

    return cleaned.strip()


def render_sources(evidence, title: str | None = None) -> None:
    if not evidence:
        return
    expander_title = title if title is not None else t("sources_used", language)
    with st.expander(expander_title):
        for i, item in enumerate(evidence, 1):
            page = t("page_indicator", language, page=item.page) if item.page else ""
            url_str = getattr(item, "source_url", "") or ""
            link_html = f' &middot; <a href="{url_str}" target="_blank" rel="noopener noreferrer" style="color: #4A90E2; text-decoration: none;">{url_str}</a>' if url_str else ""
            safe_text = clean_markdown(item.text[:650])
            st.markdown(
                f'<div class="source-card"><b>[{i}] {item.source}</b>{page}{link_html}<br>{safe_text}</div>',
                unsafe_allow_html=True,
            )


@st.cache_resource
def module():
    return build_module()


settings = Settings()
ai = module()

student_id = settings.demo_student_id
student_name = settings.demo_student_name
course = settings.demo_course
language = settings.demo_language if settings.demo_language in SUPPORTED_LANGUAGES else "en"
learning_preference = settings.demo_learning_preference

existing_profile = ai.tutor.get_student_profile(student_id)
if existing_profile is not None:
    profile = existing_profile
else:
    profile = ai.sync_learning_context(
        student_id,
        student_name,
        course,
        language,
        learning_preference,
    )

course = profile.student.course
language = profile.student.preferred_language
learning_preference = profile.student.learning_preference

# Local theme switch for the demo. In final integration the host site can pass
# the active theme and set this state automatically.
top_left, top_right = st.columns([7.6, 2.4])
with top_right:
    st.markdown(f'<div class="theme-label">{t("appearance", language)}</div>', unsafe_allow_html=True)
    theme_choice = st.segmented_control(
        "Appearance",
        options=["☀️ Light", "🌙 Dark"],
        default="🌙 Dark" if st.session_state.dark_mode else "☀️ Light",
        label_visibility="collapsed",
        key="theme-choice",
    )
    st.session_state.dark_mode = theme_choice == "🌙 Dark"

inject_theme(st.session_state.dark_mode)

with top_left:
    st.markdown(
        f"""
        <div class="feature-head">
            <div>
                <div class="feature-title">{t("app_title", language)}</div>
                <div class="feature-subtitle">{t("app_subtitle", language)}</div>
                <div class="context-line">
                    <span class="context-chip">{profile.student.course}</span>
                    <span class="context-chip">{LANG_NAMES.get(profile.student.preferred_language, profile.student.preferred_language)}</span>
                    <span class="context-chip">{get_style_display(profile.student.learning_preference, language)}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander(t("student_profile_preferences", language)):
    col_pref1, col_pref2, col_pref3, col_pref4 = st.columns(4)
    with col_pref1:
        active_course = st.text_input(t("course", language), value=profile.student.course, key="pref_course")
    with col_pref2:
        lang_keys = list(LANG_NAMES.keys())
        active_lang_key = st.selectbox(
            t("language", language),
            options=lang_keys,
            format_func=lambda k: LANG_NAMES[k],
            index=lang_keys.index(profile.student.preferred_language) if profile.student.preferred_language in lang_keys else 0,
            key="pref_lang",
        )
    with col_pref3:
        style_opts = ["step-by-step", "socratic", "visual", "analogy-first", "code-first"]
        active_style = st.selectbox(
            t("learning_preference", language),
            options=style_opts,
            format_func=lambda s: get_style_display(s, language),
            index=style_opts.index(profile.student.learning_preference) if profile.student.learning_preference in style_opts else 0,
            key="pref_style",
        )
    with col_pref4:
        st.write("")
        st.write("")
        if st.button(t("save_preferences", language), key="btn_save_pref"):
            profile = ai.sync_learning_context(
                student_id=student_id,
                name=student_name,
                course=active_course.strip() or "General",
                language=active_lang_key,
                learning_preference=active_style,
            )
            st.success(t("preferences_updated", language))
            st.rerun()

course = profile.student.course
language = profile.student.preferred_language
learning_preference = profile.student.learning_preference

# This navigation is local to the AI Tutor feature. The host application owns
# the global navbar/sidebar and authentication UI.
# Navigation tabs: AI Tutor, My Learning, Course Materials, Study Tools
tutor_tab, learning_tab, materials_tab, tools_tab = st.tabs(
    [
        t("tab_tutor", language),
        t("tab_my_learning", language),
        t("tab_course_materials", language),
        t("tab_study_tools", language),
    ]
)

with tutor_tab:
    indexed_materials = ai.list_course_materials(student_id)
    label_to_id = {m.filename: m.document_id for m in indexed_materials}

    control_a, control_b = st.columns([4, 2])
    with control_a:
        st.caption(t("ask_about_lecture", language))
    with control_b:
        selected_labels = st.multiselect(
            t("use_materials", language),
            list(label_to_id.keys()),
            label_visibility="collapsed",
            placeholder=t("all_course_materials", language),
        ) if indexed_materials else []

    mode_col, voice_col = st.columns([3, 3])
    with mode_col:
        mode_options = ["Direct Explanation", "Socratic Guidance"]
        tutoring_mode = st.radio(
            t("tutoring_style", language),
            mode_options,
            format_func=lambda m: get_mode_display(m, language),
            horizontal=True,
            key="tutoring_mode",
        )
    with voice_col:
        with st.expander(t("voice_question", language)):
            voice_file = st.file_uploader(
                t("upload_voice_recording", language),
                type=["wav", "mp3", "ogg"],
                key="voice_uploader",
                help=t("voice_help", language),
            )
            if voice_file is not None and st.button(t("process_voice_query", language), key="btn_process_voice"):
                with st.spinner(t("processing_speech", language)):
                    v_res = ai.ask_voice_tutor(
                        student_id=student_id,
                        course_id=course,
                        audio_data=voice_file.read(),
                        document_ids=[label_to_id[x] for x in selected_labels],
                        language=language,
                    )
                    if v_res.success:
                        st.session_state.messages.append({"role": "user", "content": f"🎙️ {v_res.transcription}"})
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": v_res.answer,
                            "sources": v_res.tutor_response.evidence,
                            "abstained": v_res.tutor_response.abstained,
                        })
                        if v_res.audio_path and Path(v_res.audio_path).exists():
                            st.audio(v_res.audio_path)
                        st.rerun()
                    else:
                        st.error(t("voice_error", language, error_message=v_res.error_message))

    if not indexed_materials:
        st.info(t("guidance_no_materials", language))
    else:
        st.caption(t("guidance_with_materials", language))

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(clean_markdown(message["content"]))
            if message.get("sources") and not message.get("abstained", False):
                render_sources(message["sources"])

    prompt = st.chat_input(t("ask_chat_placeholder", language))
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        query_text = prompt
        if tutoring_mode == "Socratic Guidance":
            query_text = f"[Socratic Mode: guide me step by step with questions rather than giving away the full answer immediately] {prompt}"

        recent_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
            and m.get("content").strip()
        ][-4:]

        with st.chat_message("assistant"):
            with st.spinner(t("working_on_answer", language)):
                response = ai.ask_tutor(
                    student_id,
                    course,
                    query_text,
                    language,
                    [label_to_id[x] for x in selected_labels] if selected_labels else None,
                    session_id="student-session",
                    chat_history=recent_history,
                )
            rendered_answer = response.answer
            if response.evidence and not response.abstained and hasattr(ai, "tutor") and hasattr(ai.tutor, "validator"):
                rendered_answer = ai.tutor.validator.validate_rendered_answer(
                    rendered_answer,
                    response.evidence,
                    query=query_text,
                )
            st.markdown(clean_markdown(rendered_answer))
            if response.knowledge_source == "trusted_external" and not response.abstained:
                st.caption(t("grounded_external", language))
            elif response.knowledge_source == "uploaded_material" and not response.abstained:
                st.caption(t("grounded_uploaded", language))
            if response.evidence and not response.abstained:
                render_sources(response.evidence)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": clean_markdown(rendered_answer),
                "sources": response.evidence,
                "abstained": response.abstained,
            }
        )
        st.session_state.last_topic = response.analysis.topic
        if response.assessment:
            st.session_state.assessment = response.assessment
        st.rerun()


with learning_tab:
    current = ai.get_learning_profile(student_id)
    mastery = current.concept_mastery if current else {}
    strengths = current.strengths if current else []
    weak = current.weak_concepts if current else []
    gaps = current.prerequisite_gaps if current else []

    st.markdown("### My Learning")
    st.caption("A live learning profile built from your questions and knowledge checks.")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        f'<div class="metric-card"><div class="metric-kicker">Concepts tracked</div><div class="metric-value">{len(mastery)}</div></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        f'<div class="metric-card"><div class="metric-kicker">Strengths</div><div class="metric-value">{len(strengths)}</div></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        f'<div class="metric-card"><div class="metric-kicker">Focus areas</div><div class="metric-value">{len(set(weak + gaps))}</div></div>',
        unsafe_allow_html=True,
    )
    c4.markdown(
        f'<div class="metric-card"><div class="metric-kicker">Checks completed</div><div class="metric-value">{len(getattr(current, "assessment_history", []))}</div></div>',
        unsafe_allow_html=True,
    )

    if mastery:
        st.markdown("#### Concept mastery")
        st.bar_chart(mastery)
    else:
        st.info("Complete a knowledge check and your concept mastery will appear here.")

    left, right = st.columns(2)
    with left:
        st.markdown("#### Strong areas")
        if strengths:
            for item in strengths:
                st.markdown(f"✓ {item}")
        else:
            st.caption("No confirmed strengths yet.")

    with right:
        st.markdown("#### Focus next")
        focus = list(dict.fromkeys(weak + gaps))
        if focus:
            for item in focus:
                st.markdown(f"→ {item}")
        else:
            st.caption("No gaps identified yet.")

    if current:
        try:
            next_action = ai.get_next_learning_action(student_id)
        except Exception as exc:
            next_action = None
            st.caption(f"Next learning action is temporarily unavailable: {exc}")

        if next_action:
            st.markdown("#### Next Best Action")
            with st.container(border=True):
                action_label = str(next_action.action).replace("_", " ").title()
                strategy_label = str(next_action.strategy).replace("_", " ").replace("-", " ").title()

                st.markdown(f"**{action_label}**")

                if next_action.target_concepts:
                    st.markdown("**Focus**")
                    for concept in next_action.target_concepts:
                        st.markdown(f"→ {concept}")

                if next_action.reason:
                    st.markdown("**Why this is next**")
                    st.write(next_action.reason)

                if next_action.strategy:
                    st.markdown("**Learning approach**")
                    st.write(strategy_label)

                if next_action.recommended_resources:
                    st.markdown("**Recommended resources**")
                    resource_names = [
                        str(item).replace("_", " ").replace("-", " ").title()
                        for item in next_action.recommended_resources
                    ]
                    st.write(" · ".join(resource_names))

    if current and current.misconceptions:
        st.markdown("#### Concepts to revisit")
        for item in current.misconceptions:
            st.warning(item)

    if current and getattr(current, "resolved_misconceptions", []):
        st.markdown("#### Resolved Misconceptions")
        for resolved in current.resolved_misconceptions:
            st.success(f"✓ Cleared: {resolved}")

    # Spaced Repetition Due Queue
    try:
        due_reviews = ai.get_review_queue(student_id)
    except Exception:
        due_reviews = []
    if due_reviews:
        st.markdown("#### Spaced Repetition (Due for Review)")
        for item in due_reviews[:4]:
            c_rev = item.get("concept", "")
            r_col1, r_col2, r_col3 = st.columns([3, 1, 1])
            with r_col1:
                st.markdown(f"**{c_rev}** (Mastery: {item.get('mastery', 0.5):.0%}, Repetition {item.get('repetition', 0)})")
            with r_col2:
                if st.button("Remembered ✓", key=f"rec_yes_{c_rev}"):
                    ai.record_concept_review(student_id, c_rev, True)
                    st.rerun()
            with r_col3:
                if st.button("Forgot ✗", key=f"rec_no_{c_rev}"):
                    ai.record_concept_review(student_id, c_rev, False)
                    st.rerun()

    # Reactive Study Plan
    try:
        study_plan = ai.get_study_plan(student_id)
    except Exception:
        study_plan = []
    if study_plan:
        st.markdown("#### Reactive Study Plan")
        for plan_item in study_plan:
            p_badge = "🔴 High" if plan_item.get("priority") == "high" else ("🟡 Medium" if plan_item.get("priority") == "medium" else "🟢 Low")
            with st.expander(f"{p_badge}: {plan_item.get('title')}"):
                st.write(f"**Reason**: {plan_item.get('reason')}")
                st.write("**Recommended Actions**:")
                for act in plan_item.get("recommended_actions", []):
                    st.markdown(f"- {act}")

    st.markdown("#### Start a knowledge check")
    assessment_materials = ai.list_course_materials(student_id)
    assessment_label_to_id = {m.filename: m.document_id for m in assessment_materials}

    assessment_selected_labels = st.multiselect(
        "Course Material Evidence (optional)",
        options=list(assessment_label_to_id.keys()),
        default=[],
        key="assessment_selected_course_materials",
        placeholder="Select course material(s) or leave empty for trusted external search",
        help="Select one or more course materials to ground this assessment in your uploads. Leave empty to use trusted external academic sources.",
    ) if assessment_materials else []

    suggested_topic = st.session_state.last_topic or (
        current.recent_topics[-1] if current and current.recent_topics else ""
    )
    check_topic = st.text_input(
        "Topic",
        value=suggested_topic,
        placeholder="e.g. Convolutional Neural Networks",
        key="knowledge-check-topic",
    )
    if st.button(
        "Start knowledge check",
        type="primary",
        disabled=not check_topic.strip(),
        key="start-knowledge-check",
    ):
        st.session_state.assessment_result = None
        assessment_doc_ids = [
            assessment_label_to_id[label]
            for label in assessment_selected_labels
            if label in assessment_label_to_id
        ]
        with st.spinner("Preparing your questions…"):
            st.session_state.assessment = ai.create_diagnostic(
                student_id,
                check_topic.strip(),
                language,
                document_ids=assessment_doc_ids,
            )
        if st.session_state.assessment:
            st.success("Your knowledge check is ready below.")
        else:
            st.error("Cannot generate knowledge check: No trusted evidence available for this topic. Please select relevant course materials or ensure trusted search is active.")

    if st.session_state.assessment:
        assessment = st.session_state.assessment
        st.markdown("### Knowledge check")
        if getattr(assessment, "source_title", None):
            st.markdown(
                f'<span class="context-chip">Grounded in: {assessment.source_title}</span>',
                unsafe_allow_html=True,
            )
        st.caption(
            f"A short check on {assessment.topic} helps the tutor adapt the next explanation to your actual gaps."
        )

        if not assessment.questions:
            st.error(
                "The knowledge check was created without questions. "
                "Please clear it and generate a new one."
            )
            if st.button("Clear empty knowledge check", key="clear-empty-assessment"):
                st.session_state.assessment = None
                st.rerun()
        else:
            answers: dict[str, str] = {}
            with st.form("learning_diagnostic"):
                for number, question in enumerate(assessment.questions, 1):
                    st.markdown(
                        f'<div class="question-shell"><b>Question {number}</b> · {question.concept}</div>',
                        unsafe_allow_html=True,
                    )
                    if question.kind in ("mcq", "true_false") and question.options:
                        answers[question.question_id] = st.radio(
                            question.prompt,
                            question.options,
                            key=f"diagnostic-{question.question_id}",
                            index=None,
                        )
                    else:
                        dont_know = st.checkbox(
                            idk_label(language),
                            key=f"diagnostic-idk-{question.question_id}",
                            help="Choose this instead of guessing. It is treated as missing knowledge, not as a misconception.",
                        )
                        if dont_know:
                            answers[question.question_id] = idk_label(language)
                            st.caption("Recorded as: I don't know / skip")
                        else:
                            answers[question.question_id] = st.text_area(
                                question.prompt,
                                key=f"diagnostic-{question.question_id}",
                                height=100,
                                placeholder="Write your answer here…",
                            )

                submitted = st.form_submit_button(
                    "Submit answers",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                unanswered = [qid for qid, answer in answers.items() if not answer]
                if unanswered:
                    st.warning("Answer all questions before submitting.")
                else:
                    with st.spinner("Updating your learning profile…"):
                        result = ai.submit_diagnostic(student_id, assessment, answers, language)
                    st.session_state.assessment_result = result
                    st.session_state.assessment = None

    if st.session_state.assessment_result:
        result = st.session_state.assessment_result
        source_note = f"<br>Evidence source: {result.source_title}" if getattr(result, "source_title", None) else ""
        st.markdown(
            f'<div class="result-banner"><b>Knowledge check complete</b><br>'
            f'Score: {result.score:.0%} · Your learning profile has been updated.{source_note}</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Strong areas**")
            for item in result.strengths or ["No confirmed strengths yet"]:
                st.write(item)
        with c2:
            st.markdown("**Focus next**")
            for item in result.weak_concepts or ["No major gaps detected"]:
                st.write(item)
        if result.misconceptions:
            st.markdown("**Misconceptions detected**")
            for item in result.misconceptions:
                st.warning(item)
        if result.unknown_concepts:
            st.markdown("**Not known yet**")
            for item in result.unknown_concepts:
                st.info(item)
        if result.recommendations:
            st.markdown("**Recommended next step**")
            for item in result.recommendations:
                st.write(f"• {item}")
        if st.button("Refresh learning dashboard", key="refresh-learning-dashboard"):
            st.rerun()
        if st.button("Dismiss result", key="dismiss-assessment-result"):
            st.session_state.assessment_result = None
            st.rerun()

with materials_tab:
    st.markdown(f"### {t('materials_title', language)}")
    st.caption(t("materials_subtitle", language))

    uploaded = st.file_uploader(
        t("upload_course_material", language),
        type=["pdf", "docx", "pptx", "txt", "md"],
        help=t("uploader_help", language),
    )

    if uploaded is not None and st.button(t("add_material", language), type="primary"):
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(uploaded.getbuffer())
            tmp_path = tmp_file.name
        try:
            with st.spinner(t("indexing_material", language)):
                meta = ai.upload_course_material(student_id, tmp_path, uploaded.name)
            st.success(t("material_ready_notification", language, filename=meta.filename))
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    materials = ai.list_course_materials(student_id)
    st.markdown(f"#### {t('available_materials', language)}")
    if not materials:
        st.info(t("no_materials_yet", language))
    else:
        for material in materials:
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f"**{material.filename}**")
                    details = []
                    if material.pages:
                        if material.pages == 1:
                            details.append(t("pages_count_single", language, pages=material.pages))
                        else:
                            details.append(t("pages_count_multiple", language, pages=material.pages))
                    details.append(t("indexed_for_tutor", language))
                    st.caption(" · ".join(details))
                with right:
                    st.markdown(f'<span class="status-ready">{t("status_ready", language)}</span>', unsafe_allow_html=True)

with tools_tab:
    st.markdown("### Study Tools")
    st.caption("Turn any topic into focused study material using your current learning context.")

    default_topic = st.session_state.last_topic or (
        profile.recent_topics[-1] if profile.recent_topics else ""
    )
    resource_topic = st.text_input(
        "Topic",
        value=default_topic,
        placeholder="e.g. CNN, recursion, SQL joins",
        key="resource-topic",
    )

    tools_materials = ai.list_course_materials(student_id)
    tools_label_to_id = {m.filename: m.document_id for m in tools_materials}
    selected_tools_labels = st.multiselect(
        "Course Material Evidence (optional)",
        options=list(tools_label_to_id.keys()),
        default=[],
        key="study_tools_selected_course_materials",
        help="Select one or more course materials to ground generated resources in your uploads. Leave empty to use trusted external academic sources.",
    )
    tools_doc_ids = [tools_label_to_id[lbl] for lbl in selected_tools_labels] if selected_tools_labels else None

    st.markdown("#### Choose resources")
    cols = st.columns(4)
    selected_tools = []
    for idx, kind in enumerate(TOOL_LABELS):
        with cols[idx % 4]:
            checked = st.checkbox(
                TOOL_LABELS[kind],
                value=kind in ("summary", "quiz"),
                key=f"tool-{kind}",
            )
            if checked:
                selected_tools.append(kind)

    if st.button(
        "Generate resources",
        type="primary",
        disabled=not resource_topic.strip() or not selected_tools,
        key="generate-resources",
    ):
        with st.spinner("Creating your study resources…"):
            outputs, _ = ai.generate_learning_resources(
                student_id,
                resource_topic.strip(),
                selected_tools,
                language,
                document_ids=tools_doc_ids,
            )
        st.session_state.generated_outputs = outputs

    outputs = st.session_state.generated_outputs
    if outputs:
        st.markdown("#### Generated resources")
        for kind, resource in outputs.items():
            title = TOOL_LABELS.get(kind, kind.title())
            with st.container(border=True):
                st.markdown(f"**{title}**")
                if resource.get("sources"):
                    st.caption(f"Sources: {', '.join(resource['sources'])}")
                if resource.get("type") == "text":
                    st.markdown(
                        clean_markdown(
                            resource.get(
                                "content",
                                "",
                            )
                        )
                    )
                elif resource.get("type") == "file":
                    file_path = Path(resource["path"]) if resource.get("path") else None

                    # Explicit artifact contract fields with robust file-path fallback
                    download_bytes = resource.get("download_bytes")
                    if download_bytes is None and file_path and file_path.exists():
                        download_bytes = file_path.read_bytes()
                    elif isinstance(download_bytes, str):
                        download_bytes = download_bytes.encode("utf-8")

                    filename = resource.get("filename") or (file_path.name if file_path else f"{kind}.bin")
                    mime = resource.get("mime_type") or resource.get("mime") or "application/octet-stream"
                    suffix = Path(filename).suffix.lower()

                    if download_bytes is None:
                        st.error(
                            "This generated file is no longer available. Generate it again."
                        )
                        continue

                    if kind == "diagram" and (suffix == ".svg" or mime == "image/svg+xml"):
                        st.markdown("##### Diagram Preview")

                        preview_svg = resource.get("preview_svg")
                        if not preview_svg and file_path and file_path.exists():
                            preview_svg = file_path.read_text(encoding="utf-8")
                        elif not preview_svg and isinstance(download_bytes, (bytes, bytearray)):
                            try:
                                preview_svg = download_bytes.decode("utf-8")
                            except Exception:
                                preview_svg = None

                        if preview_svg:
                            svg_b64 = base64.b64encode(preview_svg.encode("utf-8")).decode("ascii")
                            data_uri = f"data:image/svg+xml;base64,{svg_b64}"

                            st.markdown(
                                f"""
                                <div style="
                                    width:100%;
                                    background:#ffffff;
                                    border:1px solid rgba(120,120,120,.24);
                                    border-radius:14px;
                                    padding:12px;
                                    overflow-x:auto;
                                    margin:8px 0 14px 0;
                                ">
                                    <img
                                        src="{data_uri}"
                                        alt="{title}"
                                        style="
                                            display:block;
                                            width:100%;
                                            min-width:900px;
                                            height:auto;
                                            margin:0 auto;
                                        "
                                    />
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.download_button(
                            label="Download Diagram",
                            data=download_bytes,
                            file_name=filename,
                            mime="image/svg+xml",
                            key=f"download-{kind}-{filename}",
                        )

                    elif kind == "presentation" or suffix == ".pptx":
                        st.download_button(
                            label="Download Presentation Deck",
                            data=download_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            key=f"download-{kind}-{filename}",
                        )

                    elif mime.startswith("image/"):
                        if file_path and file_path.exists():
                            st.image(
                                str(file_path),
                                caption=title,
                                use_container_width=True,
                            )

                        st.download_button(
                            f"Download {title}",
                            data=download_bytes,
                            file_name=filename,
                            mime=mime,
                            key=f"download-{kind}-{filename}",
                        )

                    else:
                        st.download_button(
                            f"Download {title}",
                            data=download_bytes,
                            file_name=filename,
                            mime=mime,
                            key=f"download-{kind}-{filename}",
                        )
                else:
                    st.info(resource.get("message", "This resource is not available right now."))

    saved_resources = getattr(current, "generated_resources", [])
    if saved_resources:
        st.markdown("#### Saved Study Resources")
        with st.expander(f"📚 View previously generated study resources ({len(saved_resources)} sessions)"):
            for idx, saved_entry in enumerate(reversed(saved_resources)):
                st.markdown(f"**Topic: {saved_entry.get('topic', 'General')}** ({saved_entry.get('timestamp', '')[:16]})")
                saved_items = saved_entry.get("outputs", {}) or saved_entry.get("resources", {})
                for k, v in saved_items.items():
                    st.caption(f"Resource type: {TOOL_LABELS.get(k, k)}")
                    if v.get("type") == "text":
                        st.markdown(clean_markdown(v.get("content", "")[:400] + ("..." if len(v.get("content", "")) > 400 else "")))
                    elif v.get("type") == "file":
                        fpath = Path(v.get("path", "")) if v.get("path") else None
                        s_bytes = v.get("download_bytes")
                        if s_bytes is None and fpath and fpath.exists():
                            s_bytes = fpath.read_bytes()
                        elif isinstance(s_bytes, str):
                            s_bytes = s_bytes.encode("utf-8")
                        s_name = v.get("filename") or (fpath.name if fpath and fpath.name else f"{k}.bin")
                        s_mime = v.get("mime_type") or v.get("mime") or "application/octet-stream"
                        if s_bytes is not None:
                            st.download_button(
                                f"Download {TOOL_LABELS.get(k, k)} ({s_name})",
                                s_bytes,
                                file_name=s_name,
                                mime=s_mime,
                                key=f"saved-dl-{idx}-{k}-{s_name}",
                            )
                st.divider()

st.write("")
with st.expander("ℹ️ System Capabilities & Status"):
    caps = ai.get_supported_capabilities()
    st.write(f"**Content Generation Formats (14)**: {', '.join(caps.get('content_types', []))}")
    st.write(f"**Supported Languages (10)**: {', '.join(caps.get('languages', []))}")
    st.write(f"**Neural Vector Embeddings**: {'Active (SentenceTransformers MiniLM)' if caps.get('neural_embeddings') else 'Offline / Deterministic'}")
    st.write(f"**Optical Character Recognition (OCR)**: {'Active' if caps.get('ocr') else 'False (Text-layer native ingestion only)'}")
    st.write(f"**Realtime Streaming Voice**: {'Active' if caps.get('realtime_voice') else 'False (Push-to-talk audio supported)'}")
    st.write(f"**Primary Intelligence Router**: {caps.get('primary_provider', 'local-router')}")