# How BuzDev Handles a User Request — Agent Workflow Documentation

*Version 1.1 — October 3, 2026. Adds: job lifecycle monitoring (heartbeats, watchdog, DB-side reaper via pg_cron, ops alerting to Telegram), attempt transparency, multi-vertical playbook as the default research posture, quality harness with auto-rerun, managed-source ladder. Baseline v1.0 (Oct 2) retains structure; changed sections marked.*

---

## 1. Overview

When a BuzDev user submits a request (a lead-generation job), it lands in the `jobs` table on Supabase and is surfaced to me (the Hermes Agent acting as your AI manager) via a polling cronjob. I claim the job, research organizations and decision-makers matching the described ICP using the multi-vertical playbook, score the leads, and post a structured JSON result back through the BuzDev webhook, which the dashboard renders to the end user.

High-level flow:

```
User submits job (BuzDev dashboard)
  → jobs row created in Supabase (status: queued → dashboard shows "Request Sent")
  → cron polls /api/poll-pending → sees pending job → wakes me (Telegram)
  → I claim (status running, last_heartbeat seeded → "Processing")
  → research (heartbeat after EVERY research step) → score → build output JSON
  → POST /api/webhook (completed → "Completed") → user sees leads on dashboard
```

**Job lifecycle monitoring (v1.1):** a job can never die silently. While a job is being
processed I send heartbeats; if heartbeats stop >12 min (or a claim ages >45 min with
no heartbeat), the server watchdog requeues the job automatically (max 3 attempts,
then a visible `failed` with a resubmit message). The reaper also runs **inside the
database via pg_cron every 10 minutes** (migration `ops_events_and_reaper.sql`), so
recovery works even if the agent itself is down. Every requeue/fail event is written
to `ops_events` and surfaced to you on Telegram by the poll cron. The dashboard shows
retry context: "Retrying (attempt 2 of 3)".

---

## 2. Triggers & Scheduling

| Component | Detail |
|---|---|
| Cronjob | `buzdev-poll-60s` (id `bbd497163360`) |
| Script | `/opt/data/scripts/buzdev_poll.sh` (+ `buzdev_ops_check.py` for ops alerts) |
| Cadence | Currently every **5 minutes** (reduced from 60s for low traffic; increase back to 60s when you say traffic grew) |
| Wake behavior | Wakes the agent when a job is pending **or** when unnotified `ops_events` exist (stuck-job requeues/failures) |
| Heartbeat helper | `/opt/data/scripts/buzdev_heartbeat.sh <job_id>` — called from inside the processing loop, not on a timer |
| Server reaper | Vercel cron daily backstop (`/api/cron/reap`) + **pg_cron every 10 min in Supabase** (authoritative) |
| Support mail | Separate cron `buzdev-support-email-watch` (5m, `openmail_check.py`) notifies Telegram on new support email; you dictate replies, I send via OpenMail API with `threadId` |

Polling is the reliable path. A webhook notification from BuzDev is fire-and-forget and treated as a hint only, never as the source of truth.

---

## 3. Step-by-Step Workflow

### Step 0 — Context load
On wake, I load the `buzdev-queue-processing` skill (and `references/integrations.md` when social/Buffer work is involved). This gives me endpoints, secrets locations, the lead schema, and the quality rules without needing any of it in the prompt.

### Step 1 — Poll & see what's pending
`GET https://buzdev.vercel.app/api/poll-pending` with header `X-Webhook-Secret` (secret at `/opt/data/.buzdev/agent_secret.txt`).
- Response `{pending: false}` → check `OPS_ALERT` lines from `buzdev_ops_check.py` (unnotified watchdog events → notify you on Telegram) → end.
- Response `{pending: true, job: {id, prompt, input}}` → proceed.

### Step 2 — Atomic claim
`POST /api/poll-pending` with `{"job_id": "..."}`.
- `claimed: true` → we own the job (this also seeds `last_heartbeat`).
- `claimed: false` → someone else took it; skip immediately.

### Step 3 — Understand the request
Read `job.prompt` and `job.input`. Build the ICP picture: target vertical, geography, company size, decision-makers. This becomes the `profiles` array.

### Step 4 — Research — multi-vertical playbook (v1.1 default; proven 11→50 on the Cambodia rerun)
Run **ALL** verticals, every job (registry-first where applicable):
1. **Direct ICP** businesses exactly matching the customer profiles
2. **Retail/geography** — venues, markets, malls, districts where the ICP buys/sells
3. **Feeder institutions** — the communities/organizations that drive the ICP's demand
4. **Supply chain** — wholesalers, suppliers, tailors, regional vendors
5. **Platform-scoped social** — facebook/instagram/tiktok/threads/reddit via Tavily `include_domains` + managed MCP
6. **Channels** — groups/hashtags/discussions (new `channel` lead type)

**Rules:** directory/list pages get fully mined (all entries with contacts, not just the top hit — the single biggest win on Cambodia); contact-first curation (drop contactless entries, backfill until targets met); if a vertical yields <5 contactable leads, rung-widen once (L2) and move on. **Heartbeat after every research step.**

### Step 5 — Score & structure
Each lead gets `fit_score` (1–10) against the matched ICP. Leads are typed (`lead_type: organization|person|channel`) and tagged with their `search_rung` (L1–L4).

### Step 6 — Quality gate + harness
Verify against the quality target (§6). After delivery, read back **computed** count/coverage from the DB; if leads < 30 or coverage < 60%, perform **one free automatic rerun** with a wider strategy before treating the job as done (record `rerun_performed` in `quality_gate`). Never pad or fabricate.

### Step 7 — Deliver
`POST /api/webhook` with `{job_id, status: "completed", output}` where output contains a ```json block with keys: `business_summary`, `profiles`, `quality_gate`, `leads[]`.
On unresolvable failure: same endpoint with `{job_id, status: "failed", error}` — the error is shown on the user's dashboard. The webhook is idempotent.

### Lead schema (every entry)

```
name, email, phone, address, website, source (URL found at),
profile (matched ICP), fit_score (1-10), notes, contact_person,
person_role, social_platform, social_handle, person_email,
person_phone   — all fields nullable
```

---

## 4. Skills, Tools & Integrations Used

### Skill
- **`buzdev-queue-processing`** — the operating manual: endpoints, claim semantics, schema, multi-vertical playbook, heartbeat/quality-harness rules. Companion `references/integrations.md` holds Buffer/social credentials.

### Credentials & their homes (`/opt/data/.buzdev/`, all chmod 600)
- `agent_secret.txt` — BuzDev webhook secret (poll + webhook + cron/reap APIs)
- `supabase.env` — service-role key for direct REST access (`https://utwfxabjihhsyknfartk.supabase.co/rest/v1/`, tables: `jobs`, `leads`, `master_leads`, `ops_events`, `notification_queue`, freemium tables)
- `tavily.env` — TAVILY_API_KEY for lead research
- `stripe.env` (live), `vercel.env` + `vercel_secrets.json`, `github.env` (Netflypsb fine-grained PAT, expires 2026-12-31)
- `openmail.env` + `openmail_support.env` — support inbox `buzdev-support@omail.sh` (inbox id `d138fadb-cf74-4927-b5dd-8e13bb4119d2`)
- SerpApi key: stored in repo/worker envs (buzdev-data MCP, cap 10 calls/job)

### APIs
- **BuzDev API** (`buzdev.vercel.app`): poll-pending GET/POST, webhook POST, `/api/cron/reap` — job lifecycle backbone.
- **Supabase REST** (service-role key): direct DB reads/writes for debugging, backfills, queue + ops_events inspection.
- **Tavily Search** (primary engine; `include_domains`, `search_depth: 'advanced'`, budget ~10 calls/job).
- **buzdev-data MCP** (budget-capped; pass `job_id` on every call): `serp_search` (SerpApi), `maps_search` (KeyAPI), `discover_email`, `social_profile`, `web_search`.
- **reverse CLI** (opportunistic free extras only, never load-bearing): `microsoft_ads search-ads`, `youtube search`. On `ok:false` — skip for the rest of the job; UNAVAILABLE ≠ no results.
- **OpenMail API** (`/v1/inboxes/send`): sending support replies, `threadId` to stay in-thread.
- **Buffer GraphQL** (`api.buffer.com/graphql`, Bearer `BUFFER_API_KEY`): promo post automation (REST retires 2027-02-01).
- **Vercel API** (POST `/v13/deployments`, `gitSource` repoId `1401002082`, rootDirectory `src`, **`target: "production"` mandatory**): deploys; commit in `/opt/data/workspace/buzdev_git` → push → deploy from sha.
- **GitHub** (fine-grained PAT): repo/push operations.

### Tools (Hermes runtime)
- `execute_code` — batched API calls, loops, JSON assembly, dedupe/aggregation.
- `terminal` — cron scripts, curl, git.
- `web_search` / `web_extract` — complementary keyless search when Tavily coverage is thin.
- `cronjob` — poll + support-mail watchers.
- `memory` + skills — durable context so no job starts from zero.

**Source policy (v1.1):** managed APIs only. No anonymous scraping of Facebook/LinkedIn/Reddit/Twitter/Instagram/Threads and no browser-impersonation tools; BrightData/SocialCrawl are retired. See `docs/SOURCE_POLICY.md` in the repo.

---

## 5. Research Strategy

**Principle:** multi-vertical playbook (§3 Step 4) is mandatory on every job — this is what took the Cambodia job from 11 to 50 leads. Tavily is the primary engine; the managed ladder fills gaps:

1. **Tavily** (~10 calls/job) — general + platform-scoped `include_domains`.
2. **Managed keyless** — `web_search`, `web_extract`, web-social-search MCP.
3. **buzdev-data MCP** (capped) — `serp_search` (≤10/job), `maps_search` (~2 credits, local businesses with phones/addresses), `discover_email`, `social_profile`.
4. **reverse CLI** — opportunistic free extras only.

**L1–L4 profile ladder:** start tightest-ICP (L1); widen the radius to L2/L3/L4 when yield is thin — **widening the radius, never laxing the profile**.

**Escalation passes when contactless or short:** vertical pass (Tavily social on contactless leads) → horizontal pass (next rung) → **quality-harness rerun** (one free automatic rerun if computed stats miss the bar).

**Purity rule:** unverifiable or thin leads are dropped or flagged in `notes` — no fabrication, ever.

---

## 6. Quality Assurance

**Quality target (prompt-builder v2 + zod-validated, server-computed `computed_quality_gate`):**
- ≥ **50 leads** per job (auto-rerun threshold: < 30)
- ≥ **60% contact coverage** (computed server-side, not self-reported)

**Mechanisms:**
1. **`quality_gate` + `computed_quality_gate`** — agent-reported numbers are cross-checked by server-computed stats (zod validation on webhook ingestion).
2. **Traceability** — `source`, `search_rung`, `lead_type` on every lead.
3. **Atomic claim + heartbeats + watchdog + pg_cron reaper + attempt transparency** — no silent stuck jobs; retries visible to the user and alerted to you on Telegram.
4. **Idempotent delivery** — webhook retries are safe.
5. **Failure transparency** — unresolvable errors become `status: failed` with a clear dashboard message.
6. **Dedup discipline** — aggregate/dedupe programmatically before submission.

**Known gaps / improvement candidates:**
- Contact verification (does the email exist?) — Phase 2 territory.
- Partial-result salvage (resume a crashed run instead of restarting) — planned (W1.5).
- Phase 2 paid enrichment is designed but unexercised.
- Poll cadence tuning is manual (you tell me when to change it).

---

## 7. Surrounding Operations (non-lead work I manage)

- **Deploys:** commit in `/opt/data/workspace/buzdev_git` → push → Vercel deployment from sha (`target: production`; Hobby plan: vercel crons limited to daily — the 10-min reaper lives in Supabase pg_cron instead). Latest: W1+W2 reliability/quality stack live Oct 3, commit `dd5494e`.
- **Site pages:** `/about` `/terms` `/privacy` `/contact` `/refund` live (Netflyp Sdn Bhd 13893-K).
- **Support inbox:** cron watches `buzdev-support@omail.sh`; you approve content, I send.
- **Ops alerting:** requeues/failures of stuck jobs surface in this Telegram DM within one poll cycle.
- **GitHub ops:** PAT needs Administration: Read/Write for repo creation (learned after two rounds of scope expansion).

---

## 8. Standing Conventions (how we work together)

- You provide credentials in chat; I save them to disk immediately under `/opt/data/.buzdev/` and keep them reusable.
- Communication-sensitive actions (support replies) are always your call on content.
- Product decisions are incremental — you inform me, I adjust the pipeline (e.g. poll cadence).
- Long-term project context lives in my memory + skills, not in chat scrollback.

---

*Maintained by the agent; update whenever the pipeline changes.*
