# BuzDev Incident Report: Stuck Job & Lead Quality Improvement

**Date:** October 2–3, 2026
**Scope:** Job `9db99a51` (first submission by new user, Cambodia hijab/clothing seller)
**Status:** Resolved — mitigations deployed and verified in production

---

## 1. Incident Summary

A new user submitted their first lead-generation request (Clothing / Cambodia, B2C).
Minutes after submission they reported being unable to use the product: every new
attempt returned **"You already have a request in progress."** The submitted job was
genuinely in flight, but it had become permanently stuck in `running` status with no
result, no error, and no way for the system to recover it on its own.

**Impact:** 1 user fully blocked for ~15 minutes (manually resolved). Exposure existed
for **every** user: any agent crash would have produced the same permanent lockout.

---

## 2. Timeline (UTC)

| Time | Event |
|------|-------|
| 23:23 | Job `9db99a51` created (`queued`) |
| 23:24 | Cron poll fires; cron agent run starts, discovers the job |
| 23:26:17 | Agent **claims** the job (POST `/api/poll-pending`) → status `running`, `started_at` set |
| 23:26–23:27 | Agent actively processing (scraping business URL, research tools) |
| 23:27:42 | Last tool call completes; agent run **dies mid-turn** — no "Turn ended", no result, no error written |
| 23:27+ | Job orphaned: `running` forever. `poll-pending` returns `pending: false` (job invisible to the queue). User blocked by the one-concurrent-request check. |
| 23:30 | Manual intervention: job reset to `queued` |
| 23:39:57 | The original (later-resumed) agent run completes the job legitimately — 11 leads ingested |
| 00:06 (+1d) | Rerun with expanded research: 50 leads, 100% contact coverage, all unlocked |

---

## 3. Root Cause

**Claim-then-crash with no watchdog.** The queue design had a single recovery path:
the same agent process that flipped a job to `running` was also responsible for
finishing it (`completed`/`failed`). Nothing monitored the claim in between.

Three compounding design gaps:

1. **No liveness signal** — the system could not distinguish "being worked on" from
   "worker died". `running` was a claim, not a state with evidence of life.
2. **No timeout / reaper** — a `running` job with no live worker was never requeued
   or failed; it just aged.
3. **Hard user block on stale state** — the one-concurrent-job check counted any
   `queued`/`running` job regardless of age, so an orphaned job locked the user out
   indefinitely.

Result: a single mid-turn agent crash (run aborted by the gateway; also observed:
orphaned session lease reclaimed) translated directly into a permanent user-facing
lockout.

---

## 4. Mitigations Applied (commit `95e8dff`, deployed Oct 3)

### 4.1 Heartbeats (liveness signal)
- The processing agent sends `POST /api/webhook {status: "heartbeat"}` every ~60s
  while a claimed job is being processed (`/opt/data/scripts/buzdev_heartbeat.sh`).
- Each heartbeat refreshes `jobs.last_heartbeat` (new column).
- Claim (`POST /api/poll-pending`) also seeds `last_heartbeat` at claim time.

### 4.2 Watchdog (auto-recovery)
`src/lib/job-lifecycle.ts` — `reclaimStaleJobs()` runs inside every
`GET /api/poll-pending` **and** before every new submission (`POST /api/analyze`):
- A `running` job is considered orphaned when
  - `last_heartbeat` is older than **12 minutes**, or
  - no heartbeat was ever recorded and `started_at` is older than **45 minutes**.
- Orphaned jobs are **requeued automatically** (`queued`, attempt + 1).
- After **3 attempts**, the job is marked `failed` with a clear user-facing error:
  *"Processing failed after multiple attempts (the worker stopped responding).
  Please submit the request again."*
- The watchdog never throws — a monitoring failure cannot break job pickup or
  submission. (Worst case it is inert; it can never make things worse.)

### 4.3 Retry accounting
- New `attempt` column; index `jobs_status_running_idx (status, started_at)` for
  fast orphan scans. Migration: `supabase/migrations/job_lifecycle_monitoring.sql`
  (run in Supabase SQL editor, verified live).

### 4.4 User-facing status lifecycle
Raw internal statuses are mapped to plain-language labels in the dashboard:
- `queued` → **Request Sent**
- `running` → **Processing**
- `completed` → **Completed**
- `failed` → **Failed** (with the error message rendered)

Users are never left staring at an unexplained spinner or raw status tokens.

### 4.5 Verification (production, post-deploy)
- Planted a test `running` job with a 2-hour-stale heartbeat → the next
  `poll-pending` call requeued it (`attempt: 1`). ✓
- Heartbeat on a running test job recorded `last_heartbeat` correctly. ✓
- Exhausted-retry path marks the job `failed` after 3 attempts. ✓
- Site endpoints (home, legal pages, authed APIs) healthy; auth enforcement intact.

**Post-fix failure model:** worst case for a mid-processing crash is now
"user waits ≤ ~12 minutes, job auto-retries, up to 3 attempts" — instead of
"permanent lockout requiring manual DB surgery."

---

## 5. Lead Quality: 11 → 50 Leads

The rerun (Oct 3, 00:06) replaced the first run's 11 leads with a superset of 50 —
**4.5× growth — while raising contact coverage from 73% to 100%** (avg fit 6.5/10).

### 5.1 Why the first run only produced 11 leads
- **Unscrapeable business URL.** The user's business link is a Facebook share/video
  URL; Facebook blocks scraping, so the ICP had to be built purely from the user's
  one-line description ("Selling hijab and clothes", Cambodia).
- **Narrow query surface.** The first run leaned on general/keyless searches focused
  on Phnom Penh + Kampong Cham institutions, and stopped once a plausible result set
  existed.
- **Contact-filtering interaction.** Cambodia's Cham-community institutions publish
  almost no emails/phones, so many raw finds had no contact channel and yielded
  thin value.

### 5.2 What the rerun did differently
1. **Structured multi-vertical Tavily searches (advanced depth)** — 10+ targeted
   queries across facets, not one generic query:
   - Modest fashion: hijab/abaya shops, FB-first sellers, e-tailers
   - Retail geography: markets, malls, boutiques (Phnom Penh, Siem Reap, Battambang)
   - Feeder institutions: Islamic schools, foundations, associations, community orgs
   - Supply chain: wholesalers, tailors, regional abaya vendors (Malaysia/Pakistan)
   - Platform-scoped searches (`include_domains`: facebook.com, instagram.com,
     tiktok.com) surfaced seller pages that general search misses entirely.
2. **Directory/list mining** — extracted all 48 clothing-retail entries from
   Wanderlog's Phnom Penh listing (addresses + phones), plus Cham-leader and
   marketplace aggregation pages.
3. **Reverse layer (free)** — `facebook_ads` (country=KH), YouTube, TikTok. Honest
   result: KH ad library returned only global advertisers (Alibaba, Kashkha), so it
   contributed little here — recorded transparently in the quality gate rather than
   padded.
4. **Contact-first curation.** Every final lead carries at least one verified contact
   channel (email / phone / website / social). Entries with no contact channel at
   all were dropped and replaced, which is why coverage hit 100%.

### 5.3 Composition of the 50 leads
| Segment | Examples | Role |
|---|---|---|
| Direct ICP — modest fashion sellers | T N J Fashion Style (local abaya brand), Early Hijabs, Hijab Boutique, Bismillah Shop | Demand signal, partnerships, benchmarks |
| Islamic feeder institutions | CMF, IDEA, IMAC, An-Nikmah Institute | B2C feeder communities driving hijab demand |
| Retail venues & markets | Russian/Orussey/Olympic markets, Sorya, boutiques | Wholesale sourcing + retail channels |
| Suppliers / wholesalers | Makabi Abaya (KL), Love Hijab, tailors | Supply chain & price benchmarks |

### 5.4 Takeaway
The jump wasn't a parameter tweak — it was **coverage methodology**: multi-vertical
queries + directory mining + contact-first filtering, with each lead pinned to a
live source URL. This pattern (and the "drop contactless entries" rule) should be
the default posture for future jobs in thin-data verticals. The quality gate now
reports `target_met` / `contact_coverage_final` / `reverse_used` so this standard is
measurable, not anecdotal.

---

## 6. Follow-ups

- [x] Watchdog + heartbeats deployed and verified in production
- [x] Rerun ingested; job unlocked (all 50 contacts revealed, no charge)
- [ ] Adopt the rerun's multi-vertical research posture in the default job prompt so
      first runs start at ~50 leads without a manual rerun
- [ ] Email the user (their first experience had friction; the outcome is now strong)
