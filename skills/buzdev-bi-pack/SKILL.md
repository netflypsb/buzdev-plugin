---
name: buzdev-bi-pack
description: Use when a BuzDev job reaches STEP 7 (Business Intelligence Pack). Produces the five BI sections (customer profiles, market research, competitor analysis, GTM strategy, roadmap) with honesty rules, budget cap, and goal weighting.
version: 1.0.0
category: business
---

# buzdev-bi-pack — Business Intelligence Pack Generation

Produced at STEP 7 of the BuzDev run (see buzdev-queue-processing skill for the full pipeline). The BI pack rides on research ALREADY performed during lead generation — re-searching found facts wastes budget.

## Inputs (from job.input, all optional)

- `problem_solved` — what the user sells + the pain it removes
- `how_solved_today` — the keystone: named alternatives (tools/methods) customers use now
- `business_model` — b2b_saas | b2c_d2c | marketplace | service_agency
- `business_stage` — idea_pre_revenue | early_traction | scaling
- `goal` — new_customers | market_research | competitor_analysis | partnership

Thin inputs are normal — infer from `business_description`, and SAY what you inferred. Never fabricate.

## The five sections (output in `business_intelligence.sections[]`)

| id | position | free/locked | content |
|---|---|---|---|
| customer_profiles | 1 | FREE | ICP firmographic matrix; 2–3 buyer personas (frustrations, triggers, cost of status quo); buying-committee roles from business_model |
| market_research | 2 | FREE | TAM/SAM/SOM with cited sources or labeled proxies; market maturity verdict from how_solved_today |
| competitor_analysis | 3 | LOCKED | direct/indirect/status-quo classification of how_solved_today; differentiation matrix; 3 battlecards |
| gtm_strategy | 4 | LOCKED | growth motion from model+stage; top-5 channel scorecard (fit 1–10); 3 campaign blueprints vs named alternatives |
| roadmap | 5 | LOCKED | pricing/packaging suggestion; 90-day priorities for the stage; CAC/LTV/sales-cycle benchmarks (labeled model-typical) |

Each section JSON: `{"id","position","summary" (1-line teaser shown on locked cards),"content":{"body":"markdown string"}}`.

## Honesty rules (non-negotiable)

1. Every number in market_research / roadmap carries a source URL or is labeled "estimate based on <proxy>".
2. Never fabricate company data for named competitors — only what sources show.
3. If inputs are thin, state assumptions inline.
4. If a section can't be completed in budget, return `{"status":"insufficient_data"}` — do NOT pad.

## Budget

At most 4 additional searches (competitor pricing pages, market-size reports, channel benchmarks). Total added runtime ≤4 minutes. Prefer sources already gathered in Steps 2–6.

## Goal weighting

- `market_research` → deepen section 2
- `competitor_analysis` → deepen section 3
- `partnership` → section 4 partner-led motion + feeder-org lead emphasis
- `new_customers` → default balance

## Validation before webhook

Run `scripts/bi_render.py` (plugin) to validate the BI JSON and preview rendered markdown:

```
python3 <plugin>/skills/buzdev-bi-pack/scripts/bi_render.py <output.json>
```

Checks: 5 sections present (or marked insufficient_data), ids in enum, positions 1–5, summaries ≤500 chars, bodies non-empty. Exits non-zero on failure — fix before POSTing the webhook.

## Server-side contract (what happens after the webhook)

- Sections 1–2 stored `locked=false`; 3–5 `locked=true` — enforced SERVER-SIDE, never trusted from agent output.
- One $10 unlock per job reveals leads + all sections together.
- `computed_quality_gate.bi_sections_ingested` / `bi_validation_errors` reported back — sections failing zod are dropped and counted, not silently half-ingested.