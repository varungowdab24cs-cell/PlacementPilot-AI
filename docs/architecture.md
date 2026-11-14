# PlacementPilot AI architecture

## Runtime layers

- `backend/app/main.py` creates the FastAPI application, initializes the
  database, configures CORS, and registers modular routers.
- `backend/app/routers/` contains HTTP transport and ownership validation.
- `backend/app/schemas/` contains Pydantic request/response contracts,
  separate from SQLAlchemy persistence models.
- `backend/app/services/` contains deterministic adaptive calculations,
  mastery persistence, Groq/embedding integrations, external-problem logic,
  and research analytics.
- `backend/app/models/` contains the relational domain model and relationships.
- `frontend/` contains Streamlit presentation pages and a single reusable
  HTTP client. It does not calculate mastery, score assessments, or hold
  provider credentials.

## Data flow

Assessment answers are evaluated server-side, persisted as
`StudentAnswer` rows, and trigger deterministic mastery recalculation.
`PracticeRecord` rows include both ordinary practice and self-reported
external DSA outcomes. Mastery snapshots and recommendation batches are
persisted for longitudinal analytics.

Groq receives bounded authenticated chat history and relevant mastery context.
The Hugging Face embedding service is lazy and reusable but does not yet
implement a full retrieval-augmented generation pipeline.

Research experiments persist dated configuration and one stable assignment per
student. Assessment attempts can be tagged as pre-test or post-test. The
research report layer aggregates only observed data and excludes student
identifiers from JSON/CSV outputs.

## API documentation

FastAPI generates the complete interactive OpenAPI documentation at
`http://127.0.0.1:8000/docs` and the machine-readable schema at
`http://127.0.0.1:8000/openapi.json`. The endpoint inventory is maintained in
the root `README.md`; domain-specific assumptions are documented in
`docs/adaptive_learning.md`, `docs/ai_integration.md`,
`docs/external_dsa_problems.md`, and `docs/research_evaluation.md`.
