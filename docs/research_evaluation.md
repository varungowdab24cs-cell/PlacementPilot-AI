# Phase 9 research evaluation

## Experiment design

Experiments store a name, description, evaluation start/end dates, and a
control topic sequence. Each student receives at most one assignment per
experiment. Assignment is stable because the backend persists it and uses a
deterministic experiment/student hash for the initial control-versus-
experimental allocation.

The control condition returns the configured fixed topic sequence. The
experimental condition returns the student's current adaptive learning path
or recommendations. Assessment attempts can be tagged with `pre` or `post`
when started with an experiment ID. The assessment content should be matched
in subject, topic coverage, difficulty, and length by the researcher before
data collection; the API does not claim equivalence automatically.

Researcher experiment and report endpoints require `X-Researcher-Key`, backed
by `RESEARCHER_API_KEY`. Student analytics use the student's bearer token.

## Measures

- Pre-test and post-test scores are means of observed, phase-tagged scores.
- Topic mastery timelines come from persisted mastery-history snapshots.
- Assessment completion is answered questions divided by assessment questions.
- Question timing is the mean of recorded `time_taken_seconds` values.
- DSA practice includes observed self-reported external-problem outcomes.
- Missing scores remain `null` and are excluded from the statistic requiring
  that observation. They are never converted to zero.

The aggregate JSON and CSV reports contain group summaries only. They do not
include names, emails, student IDs, or row-level participant identifiers.
Confidence intervals use two-sided 95% t intervals when at least two
observations exist; a single observation has no standard deviation or
interval. Group comparison uses Welch's independent t-test for observed
pre/post improvements when both groups have at least two observations.

## Analysis limitations

The backend does not fabricate pre-tests, post-tests, mastery snapshots, or
practice records. Empty groups and insufficient observations are reported as
missing statistics. Deterministic allocation is stable but is not a substitute
for a randomized, powered trial. Selection effects, attrition, repeated
attempts, unequal exposure, and assessment comparability can affect results.
The system must not claim adaptive-learning effectiveness until an appropriately
designed experiment has collected and analyzed actual data.

The offline `scripts/analyze_experiment.py` script accepts an anonymized
participant-level CSV with `condition`, pre/post scores, assessment completion,
DSA solved count, and topic mastery change columns. It uses Pandas and SciPy,
rejects identifying columns, preserves missing values, and emits group
summaries plus the Welch comparison.
