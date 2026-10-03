---
name: buzdev-queue-processing
description: Use when processing BuzDev jobs from the buzdev queue.
---

## When to Use
When a BuzDev queue job arrives (cron poll, webhook, or user handoff), or the user asks about the BuzDev pipeline. Also use the companion reference `references/integrations.md` for Buffer/social automation creds and endpoints.

# BuzDev Job Processing

Base URL: https://buzdev.vercel.app — all requests need header `X-Webhook-Secret`, value in /opt/data/.buzdev/agent_secret.txt (also in /opt/data/.buzdev/vercel_secrets.json context). Supabase REST base: https://utwfxabjihhsyknfartk.supabase.co/rest/v1/ (tables: jobs, leads, master_leads, notification_queue; use service-role key as apikey+Bearer for direct DB access). A cronjob `buzdev-poll-60s` (id bbd497163360) polls every 5m (reduced to 5m for low traffic — increase to 60s when user says traffic grew) via buzdev_poll.sh (plugin scripts/ops/; callable at /opt/data/scripts/buzdev_poll.sh symlink) and wakes the agent only when a job is pending.

## Flow
1. `GET /api/poll-pending` → `{pending: true, job: {id, prompt, input}}` or `{pending: false}`
2. `POST /api/poll-pending` with `{"job_id": "..."}` → `claimed: true` means we own it; `claimed: false` means skip (someone else took it)
3. Process: build ICPs from business description, search web/socials for organizations + decision makers; send a heartbeat every ~60s during this step (buzdev_heartbeat.sh <job_id>)
4. `POST /api/webhook` with `{job_id, status: "completed", output}` — output must contain a ```json block with keys: business_summary, profiles, quality_gate, leads[]
5. On failure: `POST /api/webhook` `{job_id, status: "failed", error}`

## Lead schema (each entry)
name, email, phone, address, website, source (URL found at), profile (matched ICP), fit_score (1-10), notes, contact_person, person_role, social_platform, social_handle, person_email, person_phone — nulls allowed.

## Research Tools (use for lead discovery)
Tavily API key: /opt/data/.buzdev/tavily.env (TAVILY_API_KEY). REST: POST https://api.tavily.com/search, header `Authorization: Bearer $KEY`, body {query, include_domains?, max_results, search_depth:'advanced'}.
- General web: no include_domains.
- Social research — pass include_domains: linkedin.com (professional/decision-makers), facebook.com+instagram.com (SME local businesses), reddit.com (honest opinions), x.com, tiktok.com (trends).
- Use 2-4 targeted searches per job: general org search + social platform searches for decision-makers. Tavily results complement (not replace) the keyless FreeSerp/DuckDuckGo searches; use whichever returns richer data, combine sources.

## Reverse layer (free social/ads research — use BEFORE paid tools, see skill `reverse-research`)
The `reverse` CLI is installed at /opt/data/reverse/.venv/bin/reverse (26 platforms, keyless). Invoke via
`python3 /opt/data/skills/reverse-research/scripts/reverse_run.py <platform> <command> [args...]` →
`{"ok":true,"count":N,"file":"/tmp/....json"}` (read the file) or `{"ok":false,"error_kind":...}`.
- Step 4b (every job, after Tavily general search): `facebook_ads search-ads "<ICP keywords>" --country MY` → advertisers as warm leads (+1 fit_score, note "active advertiser", landing domain → website, WhatsApp link → phone). Optionally `microsoft_ads search-ads "<kw>"` / tiktok for B2C.
- Step 4d (enrichment, free first): missing decision-maker → `linkedin company-people <slug>`; missing contact on SME → `facebook_ads page-ads <page_id>`; thin context → `reddit search "<org> <location>"`. Fallback = existing Tavily social passes.
- Vertical pass: try `facebook_ads page-ads`, `reddit search`, `youtube search` on the org BEFORE Tavily social searches.
- Errors: treat `ok:false` as "unavailable", NEVER "no results". 429 → stop that platform's batch; blocked → one retry max then fall back; session_required/not_installed → skip layer. Never block a job on reverse.
- Quality gate: add `"reverse_used": true, "reverse_leads_contributed": <N>`.
- Dedupe reverse ads leads against Tavily orgs by normalized URL/phone/name+address.

## Quality Target (since Oct 2, in prompt-builder)
Every job targets >=50 leads with >=60% contact coverage. Pipeline: L1-L4 profile ladder (widen radius, never lax the profile), vertical pass (Tavily social search on contactless leads), horizontal pass (next rung), then Phase 2 paid tools if still weak. Leads carry lead_type (organization|person) and search_rung (L1-L4). Report target_met/contact_coverage_final in quality_gate; if <50, state why — never pad or fabricate.

## Heartbeat (mandatory since Oct 3 — in the processing loop, not a timer)
After claiming (POST poll-pending → claimed:true sets last_heartbeat), send a heartbeat at the END OF EVERY research step/tool batch: `bash /opt/data/scripts/buzdev_heartbeat.sh <job_id>`. Rule: one heartbeat per vertical (per Tavily/search batch), so the last heartbeat is never >2 min old while work continues. If heartbeats stop >12 min the server watchdog requeues the job automatically (max 3 attempts, then failed) — a dead agent run must never leave a job stuck in `running`.

## Quality harness (post-completion, every production job)
After the webhook, read back the job's computed lead count + contact coverage (leads table). If leads < 30 OR coverage < 60%: perform ONE free automatic rerun with a wider/different strategy before treating the job as done; record `rerun_performed: true` in quality_gate. Report in the completion summary: sources_used, sources_unavailable, lead_count, computed coverage.

## Rules
- Claim before processing (atomic; prevents double work)
- Send heartbeats every ~60s during processing (see above)
- Webhook is idempotent and safe to retry
- Polling is the reliable path; webhook notification is fire-and-forget
- Polling cadence: every 60s via cronjob
- Unresolvable errors → mark job failed with a clear error message (shown on user's dashboard)

## Pipeline
Business description → ICPs (profiles) → web/social search for orgs & decision makers → fit_score each lead → JSON block → webhook.