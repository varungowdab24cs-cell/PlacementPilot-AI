# PlacementPilot AI

PlacementPilot AI is an AI-powered adaptive tutor for placement preparation. It
will provide personalized practice, learning resources, and progress guidance.
Phase 5 adds the deterministic adaptive learning engine. The backend now
aggregates assessment and practice history into topic mastery, stores mastery
and recommendation history, generates prerequisite-aware learning paths, and
serves explainable personalized recommendations. Adaptive scoring does not use
an LLM.

## Proposed architecture

- **Backend:** FastAPI application in `backend/app/`, organized into routers,
  schemas, services, core configuration, authentication, database access, and
  SQLAlchemy models.
- **Frontend:** Streamlit application in `frontend/`, with page, component, and
  service modules.
- **Data:** Curated questions and learning resources in `data/`.
- **Assessment engine:** Assessment sessions are represented by authenticated
  `AssessmentAttempt` records. Answer keys remain server-side until submission.
- **Adaptive engine:** Python services calculate configurable mastery scores
  from accuracy, consistency, and practice completion, then persist the
  resulting evidence and recommendations.
- **AI tutoring:** Groq provides context-aware tutoring through authenticated
  chat sessions. Sentence-transformers embeddings are loaded lazily for a
  future semantic resource-retrieval layer; the adaptive engine remains the
  authority for mastery and assessment scoring.
- **External DSA practice:** Curated LeetCode and Codeforces URLs are stored as
  resources. Student outcomes are self-reported unless a future authorized
  platform integration verifies them.
- **Configuration:** Environment variables are documented in `.env.example`;
  local secrets belong in `.env` and must not be committed.

## Project structure

```text
backend/
  app/
    main.py
    database.py
    models/
    schemas/
    routers/
    services/
    core/
    utils/
  tests/
frontend/
  app.py
  pages/
  components/
  services/
data/
  questions/
  resources/
scripts/
```

## Setup

From the repository root, create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set local credentials and other values in `.env`. `JWT_SECRET_KEY` must be at
least 32 characters. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Never commit `.env`.

## Run locally

Start the FastAPI backend:

```powershell
uvicorn backend.app.main:app --reload
```

Start the Streamlit frontend in a second terminal:

```powershell
streamlit run frontend/app.py
```

The backend API documentation is available at `http://127.0.0.1:8000/docs`.
The frontend uses `BACKEND_URL` for the FastAPI base URL and defaults to
`http://127.0.0.1:8000`. It stores only the short-lived access token in
Streamlit session state; Groq and Hugging Face credentials remain backend-only.

Seed the development sample question bank:

```powershell
python -m scripts.seed_sample_data
```

The sample dataset is stored in
`data/questions/sample_questions.json`; every seeded question is marked as a
sample question.

## Testing

Run the backend tests from the repository root:

```powershell
pytest
```

Research analysis can be run on an anonymized participant-level CSV:

```powershell
python scripts/analyze_experiment.py anonymized_experiment.csv --output report.json
```

The statistical assumptions, experiment conditions, anonymization rules, and
limitations are documented in `docs/research_evaluation.md`.

## Current API endpoints

- `GET /health` - returns API health status.
- `POST /auth/register` - register a student.
- `POST /auth/login` - authenticate and receive a bearer access token.
- `GET /students/me` - retrieve the authenticated student's profile.
- `PATCH /students/me` - update the authenticated student's profile.
- `POST|GET /subjects` - create or list subjects.
- `GET|PATCH|DELETE /subjects/{subject_id}` - manage one subject.
- `POST|GET /topics` - create or list topics, optionally filtered by subject.
- `GET|PATCH|DELETE /topics/{topic_id}` - manage one topic.
- `POST /questions` - create an MCQ question.
- `GET /questions` - list questions with subject, topic, and difficulty filters.
- `GET|PATCH|DELETE /questions/{question_id}` - manage one question.
- `POST /assessments` - create an assessment from stored questions.
- `GET /assessments` - list assessments.
- `POST /assessments/{assessment_id}/start` - start an authenticated attempt.
- `POST /assessments/{attempt_id}/submit` - submit answers and receive grading
  and topic-wise performance.
- `GET /assessments/history` - retrieve the authenticated student's completed
  assessment results.
- `GET /adaptive/mastery` - retrieve overall and topic mastery.
- `GET /adaptive/mastery/topics` - retrieve topic-wise mastery records.
- `GET /adaptive/weak-topics` - retrieve classified weak topics.
- `GET /adaptive/recommendations` - retrieve current explainable activities.
- `GET /adaptive/learning-path` - retrieve the active learning path and progress.
- `POST /adaptive/practice` - record practice completion history.
- `POST /adaptive/recalculate` - explicitly recalculate mastery and paths.
- `POST /chat/sessions` - create an authenticated tutoring conversation.
- `GET /chat/sessions` - list the authenticated student's conversations.
- `GET /chat/sessions/{session_id}/messages` - retrieve owned conversation
  messages.
- `POST /chat/sessions/{session_id}/messages` - request structured tutoring
  guidance in concept, hint, aptitude, or programming mode.
- `GET /dsa/problems` - list curated LeetCode/Codeforces problems with filters.
- `GET /dsa/problems/recommendations` - retrieve mastery-based DSA
  recommendations.
- `POST /dsa/problems/{resource_id}/attempts` - record a self-reported problem
  outcome and optional solving time.
- `GET /dsa/practice/history` - retrieve the student's external problem history.
- `GET /dsa/practice/stats` - retrieve external practice outcome statistics.
- `GET /research/student-analytics` - retrieve the authenticated student's
  pre/post, mastery-history, assessment-timing, and DSA analytics.
- `POST /research/experiments` - create a dated research experiment with a
  fixed control sequence (researcher key required).
- `POST /research/experiments/{experiment_id}/assign` - assign a student to a
  stable control or experimental condition.
- `GET /research/experiments/{experiment_id}/report` - retrieve anonymized
  aggregate research statistics (researcher key required).
- `GET /research/experiments/{experiment_id}/report.csv` - export the
  aggregate report as CSV (researcher key required).

The mastery formula, assumptions, and limitations are documented in
`docs/adaptive_learning.md`. AI provider configuration and limitations are
documented in `docs/ai_integration.md`. External DSA catalog and verification
boundaries are documented in `docs/external_dsa_problems.md`.
The layered system design and generated OpenAPI documentation are described in
`docs/architecture.md`.
