# PlacementPilot AI final QA report

Evaluation date: 2026-11-14

## Executed checks

| Check | Result |
|---|---|
| `pytest -q` | **26 passed**, 1 existing Starlette/httpx deprecation warning |
| `python -m compileall -q backend frontend scripts` | Passed |
| `git diff --check` | Passed |
| Streamlit startup and `/_stcore/health` | `HTTP 200 ok` |
| Pandas/SciPy analysis script with temporary anonymized sample CSV | Passed; produced group summaries, confidence intervals, and Welch comparison |
| Frontend test discovery | No frontend test files are present; static compilation and Streamlit startup were executed instead |
| Secret scan for literal API keys/secrets in Python code | No production credentials found; one intentional test-only Groq value is present in `backend/tests/test_ai_integration.py` |

## Covered behavior

The executed backend suite covers authentication, duplicate and invalid
credentials, protected ownership, database/health behavior, assessment
creation/start/submission/scoring, adaptive mastery formulas and
recalculation, recommendation changes, Groq mocked responses, lazy embedding
loading, DSA filters/recommendations/completion history, research assignments,
anonymized reports, and a complete registration-to-adaptive-practice workflow.

The Streamlit application compiles and launches successfully. Its pages use
the shared REST client and do not contain adaptive scoring, assessment
evaluation, or provider credentials.

## Known limitations

- No frontend test files or browser automation suite currently exists.
- Groq and Hugging Face live network/model calls are intentionally not made in
  automated tests; provider behavior is covered with mocks.
- Research reports require `RESEARCHER_API_KEY` to be configured.
- The API uses an optional SciPy import for runtime group comparisons; the
  offline analysis script requires the declared Pandas/SciPy dependencies.
- Research allocation is deterministic and stable, but is not a substitute
  for a powered randomized controlled trial.
- Assessment comparability between control and experimental content must be
  established by the researcher through experiment configuration and study
  design.
- External DSA completion remains self-reported unless a future authorized
  platform integration verifies it.
- The existing Starlette/httpx deprecation warning remains non-blocking.

No claim of adaptive-learning effectiveness is made. Actual comparable
experimental data and a properly designed evaluation are required before such
a conclusion.
