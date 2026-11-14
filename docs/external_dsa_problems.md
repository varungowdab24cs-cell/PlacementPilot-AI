# External DSA problem integration

PlacementPilot stores a curated catalog of external problems in
`data/resources/external_dsa_problems.json`. Run
`python -m scripts.seed_external_problems` to load or update that catalog.
The seeder stores official LeetCode and Codeforces URLs; it does not scrape
either platform.

## API

- `GET /dsa/problems` lists curated problems and supports `platform`, `topic_id`,
  and `difficulty` filters.
- `GET /dsa/problems/{resource_id}` returns one curated problem.
- `GET /dsa/problems/recommendations` returns deterministic recommendations for
  the authenticated student, prioritizing company-category matches and lower
  topic mastery.
- `POST /dsa/problems/{resource_id}/attempts` records `attempted`, `solved`,
  `need_help`, or `skipped`, with optional solving time.
- `GET /dsa/practice/history` returns the authenticated student's external
  problem history.
- `GET /dsa/practice/stats` returns outcome counts and average solving time.

All completions are stored with `completion_source=self_reported` and
`verified=false`. PlacementPilot never claims that a platform submission was
verified. An authorized LeetCode or Codeforces API integration can later add a
verification workflow without changing the self-reported history contract.

Solved external problems are represented as completed practice records, so
their topic-level completion data is included in the deterministic adaptive
engine. Attempted, help-needed, and skipped records remain history and affect
the practice-completion denominator without being marked complete. No custom
online judge is included.
