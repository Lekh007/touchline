# Touchline - product specification

A marketing analyst in a box: ask a business question in plain language, get
back analyst-grade SQL against a real warehouse, deterministic attribution and
incrementality numbers computed by Python (never by a model), and a cited
plain-language interpretation - or an explicit refusal when the evidence does
not support a claim.

## The one rule

**Deterministic code owns every number. The LLM investigates, explains, and
cites.** Attribution shares, RoI, lift, confidence intervals - all computed by
this repository's own modules against warehouse data. The model's output is
prose about numbers it was handed, with references to the queries and tables
that produced them. A claim with no citation is a bug, not a style choice.

## Users

1. **The marketing analyst** who today writes these SQL queries and
   spreadsheets by hand every Monday.
2. **The account lead** who needs "what did the spring campaign actually do"
   before a client call, not after a three-day analysis cycle.
3. **The interviewer** - the product must survive the question "how do you
   know the numbers are right?" with an eval suite, not a shrug.

## Surfaces

- **CLI (wave 1):** `touchline ask "which channel drove last week's revenue?"`
  → SQL + table + interpretation, all printed with provenance.
- **Eval harness (wave 2):** a question set with hand-computed expected
  answers; every prompt/model/policy change replays it. promptfoo or DeepEval
  for the LLM-as-judge layer on interpretation quality; the numeric layer is
  graded mechanically against the deterministic module's output.
- **Warehouse adapters (wave 3):** DuckDB (reference, offline) → BigQuery
  sandbox → Databricks Free Edition. Same tiny interface: `paths()`, `spend()`.
- **Cloud LLM profile (wave 4):** one recorded Bedrock or Azure OpenAI run
  against trial credits, costed and written up; a local-vs-cloud comparison
  table on the eval set is itself a product finding.
- **Governance (wave 5):** the agent's tool calls (SQL execution especially)
  pass through Turnstile - read-only by default, deny on destructive SQL,
  cost ceilings per tenant. The agent is the first real client of the policy
  gateway this portfolio is built around.

## Non-goals (v1)

- No dashboards (Metabase later, only if the BI line needs it).
- No streaming/real-time ingestion.
- No MMM (media mix modeling) - geo-lift incrementality only; MMM needs more
  data than a synthetic warehouse honestly carries.
- No multi-tenant anything. This is an analyst's tool.

## The data

Synthetic but honest: seeded generator producing channels, campaigns, daily
spend, user paths (1–6 touchpoints, realistic channel transition biases),
conversions with revenue. A known ground truth (the generator's planted
channel multipliers) makes the eval set meaningful: the agent's interpretation
can be graded against what *actually* drove conversions, not just against
internal consistency.

## Deterministic layer contract

`attribution.py`: last-touch, first-touch, linear, time-decay; conservation -
credit sums to revenue - asserted in tests. `incrementality.py` (wave 2):
geo-lift via CausalPy/PyMC with a stated identification assumption, or an
explicit "not estimable from this data" refusal. `sql.py` (wave 1): the
agent's only execution path - read-only, allow-listed statement shapes,
`TURNSTILE`-governed, per-question cost recorded.
