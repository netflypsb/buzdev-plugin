---
name: buzdev-lead-workflow
description: THE mandatory end-to-end workflow for every BuzDev lead-generation job. Routing rule SERP/Maps to find → SocialCrawl/LinkedIn to enrich → Unlocker/fetch_page the website → discover_email → export. Budget-gated. Follow this for every search job, no exceptions.
version: 1.0.0
category: business
---

# BuzDev Lead Workflow — MANDATORY ROUTING

You are generating prospective customers for a BuzDev user. Follow this pipeline in order.
Tool reference: see the `buzdev-data` skill. Budget rule lives there too.

## Phase 0 — Budget (always first)

```
set_job_budget(job_id="<job id>", cap_credits=<cap>)
```
Suggested caps: quick scan 50, standard run 200, deep run 500. Never skip this.

## Phase 1 — FIND (pick ONE primary surface)

- **Local SMEs** (clinics, restaurants, salons, contractors, retail): `maps_search`
  e.g. `maps_search(q="dental clinic Kuala Lumpur", gl="my")` → businesses with phone + website + rating.
- **National/niche B2B, service businesses, hard-to-geotag targets**: `serp_search`
  e.g. `serp_search(query="private dermatology clinics Malaysia contact")`.
- **B2B SaaS / professional firms**: `linkedin_company_search` directly (10cr — budget accordingly).

Repeat with 2–5 query variants (industry × city, synonyms) until you have 20–50 raw candidates.
Track spend; when the budget gate refuses a call, jump to Phase 5 with what you have.

## Phase 2 — ENRICH every candidate (dedupe first by website domain)

1. `linkedin_company_by_domain(domain)` (5cr) — confirm the company is real and get size/industry.
2. Skip linkedin enrichment for micro-businesses with no LinkedIn presence — do not burn credits retrying.
3. `linkedin_company_detail(identifier)` (5cr) ONLY when size/industry changes the lead's fit score.

## Phase 3 — VERIFY the website (never skip)

`fetch_page(url)` on the candidate's own website (from maps/serp/linkedin).
Reject or downrank candidates whose site is dead, parked, or irrelevant.
Extract signals for the profile gate: what they sell, team size, tech maturity, obvious pain points.

## Phase 4 — CONTACT DISCOVERY

`discover_email(url)` (free). Requires ≥1 of:
- email found on the site (high confidence), or
- phone from Google Places (maps_search already returns it), or
- a LinkedIn page (company message channel).

**Only leads with at least one verified contact channel may be exported.** Pattern-guessed emails are NOT verified — mark them low confidence or drop them.

## Phase 5 — EXPORT

Score each lead 0–100 using the user's profile criteria (industry fit, size, reachability).
Return JSON array (one row per lead):

```json
{
  "company_name": "TIHO Dental Clinic KL",
  "website": "https://tihodental.com.my/",
  "linkedin": null,
  "email": "tihodental@gmail.com",
  "email_confidence": "high",
  "phone": "+60 10-258 1285",
  "location": "Kuala Lumpur, Malaysia",
  "rating": 4.9,
  "source": "maps_search",
  "fit_score": 82,
  "notes": "5.0-rated clinic, active site, no LinkedIn — owner-operator, reachable by phone/email"
}
```

Always include: `budget_used`, `leads_found`, `leads_exported`, and if the cap was hit mid-run
say so explicitly ("stopped cleanly at X% of budget with N leads").

## Worked example (local dental clinics, cap 200)

1. `set_job_budget(job_id="job_abc", cap_credits=200)`
2. `maps_search(q="dental clinic Petaling Jaya")` ×3 city variants → 30 candidates (~6cr)
3. Dedupe by website → 24 unique. `linkedin_company_by_domain` for the 8 that look group-practice (40cr)
4. `fetch_page` the top 15 websites (0–15cr) → 12 alive
5. `discover_email` the 12 (0cr) → 9 with contacts; 3 also had phones from step 2
6. Score + export 10 leads, `budget_used=61cr`

## Hard rules

- NEVER call a paid tool with a `job_id` that has no budget set (you get the default cap — that's fine, but set a deliberate cap for real jobs).
- NEVER fetch or scrape from this agent's own IP beyond what the tools do internally — all scaling goes through the managed APIs.
- NEVER export a lead with no contact channel.
- NEVER continue searching after a `job_budget_exhausted` error — export partial results.
- Cache what you can: SocialCrawl cache hits are free — repeat identical queries cost 0.
