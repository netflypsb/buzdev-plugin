---
name: lead-generation
description: Use when a business needs prospect or partner lead lists.
category: business
version: 1.0.0
author: Hermes Agent
tags: leads, outreach, prospecting, csv, registry
related_skills: buzdev-outreach, buzdev-lead-generation, b2b-lead-harvesting, web-social-search
---

# Lead Generation — prospect sourcing & qualification

## When to Use

Use when any business (IPTIP, Genesis companies, client projects) needs a prospect/customer/partner contact list — sourcing, qualification, and CSV deliverable.

Class workflow for building contact lead lists for a client business. Tool-agnostic: Hermes `web_search`/`web_extract`, direct registry harvesting, and optionally the sme-outreach-mcp worker (that skill covers the MCP worker's own mechanics and credit gate).

## Non-negotiables (every run)

- **The client is never a lead.** Before export, assert the client company (its name AND its domain) appears in zero lead rows. The prospect class is the client's MARKET — the gatekeeper institutions whose audiences are the client's end customers (education client → feeder schools and institutional partners; B2B product → its buyers' firms), never the client itself. Delivering the client as the only "lead" fails the whole run.
- **A lead has a usable contact.** Drop rows with neither email nor phone. Pattern-guessed emails are not contacts — include only with an explicit low-confidence marker, and prefer excluding them.
- **Deliverable standard:** CSV encoded utf-8-sig (Excel-safe for non-ASCII names), priority tiering (primary market geography first), and a source URL on every row.
- **Verify before delivering:** read the export back, confirm row count and contact coverage (rows with email and/or phone), then deliver through the user's preferred channel in the same turn.

## Procedure

1. **Define the prospect class from the client's market**, not from the client's profile. State who the end customer is, then who controls access to them.
2. **Registry-first for regulated/listed niches** (schools, clinics, licensed traders, associations): search `senarai|direktori <prospect type> <state/region>` in the domain's language and target the ministry/department portal — see `references/registry-mining.md` for the harvesting recipe.
3. **Fill gaps with general web search.** For niche/local queries in non-English markets, Hermes `web_search` outperforms keyless search APIs; use it to reach schools or firms the registry misses. For local business discovery via Google Search API, see `references/serpapi-local-search.md` — SerpApi with the `location` parameter finds prospects when no registry exists. For social media presence, SocialCrawl `/v1/search/everywhere` fans a single query across 21 platforms (TikTok, IG, FB, YouTube, X, LinkedIn, Reddit). SocialAPIs.io adds FB/IG page details (email, phone, address, followers) for enrichment.
4. **Clean and dedupe:** regex-extract emails/phones, truncate label leakage, dedupe on normalized name keeping the richest contact (email > phone > first).
5. **Tier and sanity-assert:** priority by geography/relevance; assert client absent, contact coverage, and that the state/district/type distribution matches the intended filters.
6. **Export and deliver** (CSV per the deliverable standard; keep a JSON sidecar for re-export).

## Pitfalls

- **Empty or junk results from generic lead-search tools are not evidence of no leads.** Curated search indexes return zero or irrelevant results for niche/local queries in Malay/Chinese/Thai etc. — rerun the intent through Hermes web search or an official registry before concluding anything.
- **Registry filtered queries can silently drop rows.** Parse the full unfiltered list and filter locally instead of trusting server-side filters.
- **Detail-page fields beat list-page fields.** Principal/owner, phone, and email usually live only on the per-entity detail page — harvest those, not the list rows.
- **SocialCrawl redirects and uses a non-standard auth header.** The API host `socialcrawl.dev/v1/` returns a 301 — use `redirect: "follow"` in fetch or `-L` in curl, or you get an empty response. Auth is `x-api-key` header, NOT `Authorization: Bearer`. SocialAPIs.io similarly uses `x-api-token`, not Bearer. Mixing these auth headers silently fails.