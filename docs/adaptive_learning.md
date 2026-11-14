# Adaptive Learning Engine

## Scope

Phase 5 uses deterministic Python logic to convert a student's stored
assessment attempts and practice records into topic mastery, recommendations,
and a learning path. No LLM is used to calculate scores or choose activities.

## Mastery formula

For each topic, the engine calculates:

- **Accuracy:** The mean topic accuracy across completed assessment attempts.
  An attempt's topic accuracy is correct answers divided by the number of
  questions for that topic in the assessment. Unanswered questions therefore
  do not count as correct.
- **Consistency:** `100 - population_standard_deviation(attempt accuracies) *
  100`, clamped to `0..100`. Stable performance scores near 100; variable
  performance scores lower.
- **PracticeCompletion:** Completed practice records divided by all recorded
  practice records for the topic.

The initial formula is:

```text
M = 0.6 * Accuracy + 0.2 * Consistency + 0.2 * PracticeCompletion
```

The weights are configurable through `.env`:

- `MASTERY_ACCURACY_WEIGHT`
- `MASTERY_CONSISTENCY_WEIGHT`
- `MASTERY_PRACTICE_WEIGHT`

If a component has no evidence, its weight is removed and the remaining
weights are renormalized. Missing evidence is never treated as a zero score.
However, a topic remains `Insufficient data` until it has the configured
minimum number of completed assessment attempts
(`MASTERY_MINIMUM_ASSESSMENT_ATTEMPTS`, default `2`).

## Classification

- `0–39`: Weak
- `40–59`: Developing
- `60–79`: Good
- `80–100`: Strong

Topics with insufficient assessment history are not classified as weak and
have a null mastery score in API responses.

## Recommendations

Recommendations are deterministic:

1. Candidate topics are insufficient, weak, or developing topics; strong and
   good topics are not repeatedly recommended.
2. Candidates are ordered by lower mastery first, then topic name.
3. If a candidate has a prerequisite whose mastery is below the good threshold
   or insufficient, the prerequisite is inserted first.
4. Difficulty is selected from the current classification:
   - Weak: `easy`
   - Developing: `medium`
   - Insufficient: `medium`
   - Good/Strong when explicitly requested: `hard`
5. A stored resource is recommended when available; otherwise the engine
   recommends MCQ practice for the topic.

Each recalculation supersedes the previous recommendation batch and stores the
new rationale in `recommendation_history`. Assessment submission triggers
recalculation automatically. Practice completion also refreshes mastery and
recommendations without replacing the active path.

## Persistence

- `topic_mastery` stores the current topic state.
- `mastery_history` stores every calculation snapshot and formula version.
- `recommendation_history` stores recommendation batches and their rationales.
- `practice_records` supplies practice-completion evidence.
- `learning_paths` and `learning_path_items` store the generated plan and
  progress.

## Assumptions and limitations

- Phase 5 supports one prerequisite per topic. A future graph model can
  support multiple prerequisites and cycle validation.
- Assessment accuracy is based on the questions attached to each completed
  assessment attempt; there is no time-decay or recency weighting yet.
- Practice completion is an event ratio, not a quality measure. Completing a
  practice record does not imply correctness.
- A score is not produced before the minimum assessment history is available.
- Recommendation selection is rule-based and does not yet account for
  scheduling, resource difficulty metadata, student availability, or learning
  outcomes after a recommendation.
