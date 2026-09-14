# Touchline - build plan

Six waves, each ending with something that runs and tests that pass. Same
discipline as the Quarterline build: verify every wave before committing;
agents never commit.

## Wave 0 - deterministic core (done when CI is green)

- [x] `attribution.py`: last/first/linear/time-decay with the conservation contract
- [x] `db.py`: DuckDB schema, atomic conversion inserts, `paths()` / `spend()`
- [x] Hand-computed fixture tests (no snapshot tests)
- [x] `scripts/generate_synthetic.py`: seeded generator with planted channel multipliers
- [x] Gates: `uv run pytest`, `uv run ruff check src tests`, `uv run mypy src` (strict)

## Wave 1 - the SQL analyst

- Text-to-SQL against the DuckDB mirror: schema-aware prompt, read-only
  execution path (`sql.py`), per-question cost ledger
- `touchline ask` CLI: question → SQL + result table + interpretation with
  provenance (query text, row counts, table names)
- Local model (Ollama) first; quality measured, not assumed

## Wave 2 - evals and incrementality

- Eval set: ~20 questions with hand-computed numeric answers + graded
  interpretation criteria
- promptfoo/DeepEval harness wired into CI (fixtures only - no network in CI)
- `incrementality.py`: geo-lift (CausalPy) on the synthetic geos, with the
  identification assumption stated and a refusal path when the data cannot
  support the question

## Wave 3 - real warehouses

- BigQuery sandbox adapter (load jobs + CTAS only - no DML tier limits)
- Databricks Free Edition adapter (post LinkedIn verification)
- DuckDB remains the offline mirror; a `sync` command re-materialises remote
  tables locally so an expiry can't eat the corpus

## Wave 4 - the cloud question

- One recorded Bedrock or Azure OpenAI run against trial credits: dated,
  costed, torn down same day
- Local-vs-cloud comparison table on the eval set: accuracy, latency, cost
  per question - written up in the README

## Wave 5 - governed by Turnstile

- The agent's `execute_sql` tool call routed through a Turnstile policy
  (read-only allow, destructive deny with regex on the statement, budget
  ceiling per session)
- Recorded demo transcript; the audit chain shows every call the agent
  attempted, allowed or refused
