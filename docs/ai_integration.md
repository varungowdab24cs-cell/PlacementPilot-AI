# Phase 6 AI integration

## Providers and configuration

Groq is used only for conversational tutoring. Configure `GROQ_API_KEY` and
`GROQ_MODEL` in the uncommitted `.env` file. `GROQ_TIMEOUT_SECONDS` controls
the SDK timeout, and `AI_RATE_LIMIT_PER_MINUTE` applies an in-memory,
per-student request limit. Provider keys are never included in API responses or
application log messages.

`HF_EMBEDDING_MODEL` defaults to
`sentence-transformers/all-MiniLM-L6-v2`. The embedding service loads this
model lazily and caches it for reuse. It provides text and resource embedding
methods for a future semantic resource-retrieval layer; Phase 6 does not
implement RAG or persist vectors.

## Tutoring flow

An authenticated student creates a chat session, then posts messages to that
session. The backend persists the user message, selects only that student's
bounded mastery and recommendation context, and sends that context plus a
bounded recent conversation history to Groq. The assistant message is stored
only after a valid structured response is returned.

Supported modes are `concept`, `hint`, `aptitude`, and `programming`. The
response is validated as JSON with an answer and suggested actions. Timeout,
connection, provider, malformed-response, configuration, and rate-limit
failures are mapped to explicit HTTP errors.

The adaptive engine remains authoritative for mastery and official assessment
scores. The tutor prompt explicitly prohibits Groq from calculating or
modifying those values. Chat sessions and messages are filtered by the
authenticated student's ID, so a student cannot read or write another
student's conversation.

## Limitations

The rate limiter is process-local and should be replaced with a shared store
when deploying multiple API workers. Context selection is intentionally
bounded and uses stored mastery/recommendation rows; it is not a general
knowledge-base retrieval system. AI output is tutoring guidance, not an
assessment result.
