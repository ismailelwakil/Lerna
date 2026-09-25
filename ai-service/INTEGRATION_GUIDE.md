# Integration Guide — AI Learning Intelligence Module

## Ownership boundary

The host Academic Operating System owns authentication, user accounts, roles, navigation, course enrollment, permissions, and the production frontend.

This module owns learning intelligence:
- grounded AI tutoring
- course-material ingestion and retrieval
- multilingual query handling
- diagnostic assessment
- concept-level learner modeling
- personalization
- learning-resource generation
- model routing and validation

The Streamlit application under `app/` is a demo/test harness only.

## Stable integration facade

Use `src.integration.LearningIntelligenceModule` rather than importing internal services from the host application.

```python
from src.integration import build_module

learning = build_module()
learning.sync_learning_context(
    student_id='student-123',
    name='Malak',
    course='Artificial Intelligence',
    language='ar',
    learning_preference='step-by-step',
)
```

### Tutor

```python
response = learning.ask_tutor(
    student_id='student-123',
    course_id='Artificial Intelligence',
    text='اشرحلي CNN',
    language='ar',
    document_ids=[],
    session_id='web-session-id',
)
```

### Diagnostic

```python
assessment = learning.create_diagnostic('student-123', 'CNN', 'ar')
result = learning.submit_diagnostic(
    'student-123',
    assessment,
    answers={'question-id': 'answer'},
    language='ar',
)
```

### Learner knowledge

```python
profile = learning.get_learning_profile('student-123')
```

### Course material

```python
meta = learning.upload_course_material(
    'student-123',
    '/secure/temp/course.pdf',
    'course.pdf',
)
materials = learning.list_course_materials('student-123')
```

### Learning resources

```python
resources, routing = learning.generate_learning_resources(
    'student-123',
    'CNN',
    ['summary', 'quiz', 'diagram'],
    'ar',
)
```

## Host integration rules

1. The host passes the authenticated `student_id`; this module does not create accounts.
2. The host passes the currently selected/enrolled course.
3. The host performs authorization before sending files or document IDs.
4. The module persists learning state keyed by `student_id`.
5. Internal provider/vector-store details should not be shown in the normal student UI.
6. Use the facade methods above as the integration boundary so internal AI services can evolve without changing the host frontend/backend contract.

## Configuration

Copy `.env.example` to `.env`. API keys are read directly by `Settings`, so local `.env` configuration works without manually exporting shell environment variables.

## Demo UI

Run:

```powershell
streamlit run app\streamlit_app.py
```

The sidebar emulates context that would normally be supplied by the main platform. It is not an authentication interface.

## Student-facing Streamlit demo

The Streamlit application intentionally behaves as if the learner is already authenticated by the host Academic OS. It does not expose account creation, learner IDs, provider configuration, vector-store details, or developer diagnostics to the student.

For standalone demonstrations, the authenticated learner context is supplied through `DEMO_STUDENT_ID`, `DEMO_STUDENT_NAME`, `DEMO_COURSE`, `DEMO_LANGUAGE`, and `DEMO_LEARNING_PREFERENCE` in `.env`. These values exist only to simulate the host session. In production, the host backend should call the `LearningIntelligenceModule` facade using the authenticated user and enrolled-course context.

The student UI is limited to four product-facing areas: AI Tutor, My Learning, Course Materials, and Study Tools. Diagnostic assessment is embedded in the tutoring/learning flow rather than exposed as a developer-oriented subsystem.

## Frontend alignment

The Streamlit app is intentionally a feature-level demo, not a second application shell. The host Academic OS owns login, global navigation, student identity, enrolment, and global theme. The AI Tutor view consumes authenticated learner/course context and renders only its local learning experience.

For the current standalone demo, learner context is supplied through the DEMO_* settings and a local Light/Dark switch is available. During integration, map the authenticated host session to `sync_learning_context(...)` and map the host application's active theme to the Tutor view instead of displaying independent account controls.

Student-facing navigation is limited to Tutor, My Learning, Course Materials, and Study Tools. Provider names, model routing, vector-store health, API keys, and developer diagnostics are intentionally excluded from the student UI.