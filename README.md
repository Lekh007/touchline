# Touchline

**A marketing analyst in a box: business question in, analyst-grade SQL,
deterministic attribution, and a cited interpretation out — or an honest
refusal when the evidence does not support a claim.**

Every number about credit and lift is computed by deterministic Python
against a real warehouse. The LLM investigates, explains, and cites; it never
invents a figure. Same discipline as [BondLens](https://github.com/Lekh007/bondlens-cmbs-surveillance),
applied to the domain Epsilon's Account Analytics team lives in — where the
team [already runs AI agents that generate analyst-grade SQL](https://epsilon-publicisgroupe.icims.com/jobs/171303/job)
and treats evaluation harnesses as part of the job.

## Status

Wave 0 of 6 — the deterministic core:

- Attribution models (last-touch, first-touch, linear, time-decay) with a
  conservation contract: credit assigned sums to revenue converted, asserted
  on every run
- DuckDB warehouse schema (spend, conversions, ordered touchpoints) with
  atomic inserts and path streaming
- Seeded synthetic-data generator with **planted channel multipliers**, so
  interpretations can be graded against a known ground truth

Planned next: text-to-SQL analyst CLI with cost ledger (wave 1), evaluation
harness + geo-lift incrementality (wave 2), BigQuery sandbox + Databricks
Free Edition adapters (wave 3), one recorded cloud-LLM run with a
local-vs-cloud comparison table (wave 4), agent tool calls governed by
[Turnstile](https://github.com/Lekh007/turnstile) (wave 5).

## Run the gates

```bash
uv sync
uv run pytest
uv run ruff check src tests
uv run mypy src        # strict
```

## Generate the demo warehouse

```bash
uv run python scripts/generate_synthetic.py data/marketing.duckdb
```

Seeded and deterministic: the same command produces the same warehouse, and
the generator's README section documents the planted effect sizes.

## Honest scope

A portfolio project, local-first, not production software-as-a-service. The
synthetic warehouse is a stand-in for real campaign data; the identification
assumption behind any lift estimate is stated next to the estimate, and a
question the data cannot answer gets a refusal, not a confident guess.
