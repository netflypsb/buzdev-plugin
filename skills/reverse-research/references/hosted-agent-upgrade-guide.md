# BuzDev Hosted Agent — Installation & Workflow Upgrade Guide

*For the Nous Portal Hermes agent that manages BuzDev user requests.*
*Version 1.0 — October 3, 2026. Adds the `reverse-research` plugin (free ads/social research layer) and the upgraded research workflow. Maintained as a companion to `buzdev_user_request_workflow.md`.*

---

## 0. What this guide changes

| Before (v1.0 baseline) | After (this upgrade) |
|---|---|
| Research = Tavily + keyless web search only | + `reverse` CLI: **ads libraries** (Meta/Microsoft/Pinterest/Snapchat), Reddit/YouTube/Twitter/Instagram structured search, anonymous LinkedIn |
| LinkedIn people data: unavailable | `reverse linkedin` tried first, paid tools as fallback |
| Advertiser intelligence: none | **New capability** — businesses actively spending on ads = warm B2B leads with marketing budget |
| Website coverage weak (~15% of leads) | Ads-library landing domains fix this for free |
| MCP: none in use | Still none needed — reverse is a **skill + subprocess CLI**, matching your no-daemon constraint |

Nothing about the queue mechanics changes: poll → claim → research → webhook stays identical. This upgrade only changes **Step 4 (research)** and adds one install step.

---

## 1. Prerequisites check (run once)

```bash
python3 --version        # need 3.11+ (you have 3.13.5 ✓)
node --version           # need 18+ for TikTok/Zhihu signing (you have v26.5.1 ✓)
command -v uv            # preferred installer (PEP 668: no system pip) ✓
df -h /opt/data          # install needs ~200 MB
```

## 2. Install the plugin (one-time, ~3 minutes)

### 2.1 Get the skill

The skill lives in the BuzDev plugin repo (`netflypsb/buzdev-plugin`, branch `master`, commit `06b2563` or later), at `skills/reverse-research/`.

```bash
# If you already have the plugin cloned somewhere under /opt/data:
git -C <your-plugin-dir> pull origin master

# If not, clone it:
git clone --depth 1 https://github.com/netflypsb/buzdev-plugin.git /opt/data/buzdev-plugin
```

### 2.2 Run the installer

```bash
bash /opt/data/buzdev-plugin/skills/reverse-research/scripts/install.sh
```

What it does (idempotent — safe to re-run):
1. Clones the CLI source to `/opt/data/reverse/src/` (from `github.com/ifccod/social-media-research-cli`, MIT)
2. Creates a uv venv at `/opt/data/reverse/.venv` (PEP 668-safe)
3. Installs the CLI (`reverse` package) editable
4. Smoke-tests: writes the platform catalog to `/opt/data/reverse/catalog.json`

**Expected output:**
```
OK: reverse installed. Platforms in catalog: 26
Entry point: /opt/data/reverse/.venv/bin/reverse
```

### 2.3 Verify

```bash
/opt/data/reverse/.venv/bin/reverse list --json | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print('platforms:', len(d['platforms']))"
# → platforms: 26

# Real-data smoke test (Meta Ads Library — should return active advertisers):
python3 /opt/data/buzdev-plugin/skills/reverse-research/scripts/reverse_run.py \
  facebook_ads search-ads klinik
# → {"ok": true, "count": 1, "file": "/tmp/tmpXXXX.json"}
# Read the file: it contains page names, landing domains, ad status
```

### 2.4 Register the skill

Add `reverse-research` to your skill loading for BuzDev jobs (alongside `buzdev-queue-processing`). In practice: when you wake on a BuzDev job, load both:

```
skill_view(name='reverse-research')   # after installing, it auto-discovers
```

The skill file itself (`SKILL.md`) contains the full command reference, error semantics, and the free-first ladder — you don't need to memorize anything from this guide after install; the skill is the reference.

**Install notes:**
- Only `/opt/data` survives restarts — the installer already targets only `/opt/data/reverse/`. ✓
- No daemons, no listening ports, no background services. Every command is invoke → work → exit. ✓
- No API keys required — all reverse platforms are keyless/anonymous. ✓
- If install or any command fails: skip this layer silently and proceed with your normal workflow. **Never block a user job on reverse.**

---

## 3. Command syntax (the two gotchas)

Invoke via the executor wrapper, which handles file output and typed errors:

```bash
python3 <skill_dir>/scripts/reverse_run.py <platform> <command> [args...]
```

**Gotcha 1 — `--output` is a platform-level flag.** The wrapper handles this for you; if you ever call `reverse` directly: `reverse <platform> --output /tmp/x.json <command> <args>` (flag BEFORE the command).

**Gotcha 2 — many commands take POSITIONAL args, not flags.** e.g. `reverse facebook_ads search-ads "klinik"`, NOT `--query klinik`. Check the signature first:

```bash
reverse describe facebook_ads search-ads --format json   # shows exact params
```

**Executor output contract:**
- Success: `{"ok": true, "count": N, "file": "/tmp/...json"}` → **read the file** for the data (`items[]` for ads, `posts[]` for reddit, a list for youtube)
- Failure: `{"ok": false, "error_kind": "rate_limited" | "blocked" | "session_required" | "failed" | "not_installed"}` → apply the fallback ladder (§4.3); do NOT retry more than once

---

## 4. The upgraded workflow

Everything from `buzdev_user_request_workflow.md` §3 (Step 0–3, 5–7) is unchanged. **Step 4 (research) is upgraded as follows.**

### 4.1 New research order per job

```
Step 4a — Tavily general search (unchanged)          ← org discovery, 2-3 calls
Step 4b — NEW: Ads intelligence sweep                ← ~2 calls, free
Step 4c — Tavily social-domain passes (unchanged)     ← decision-makers, SMEs
Step 4d — Enrichment via reverse where applicable     ← free before paid
Step 4e — Vertical/horizontal escalation (unchanged, but now includes reverse)
Step 4f — Phase 2 paid tools (unchanged, last resort)
```

### 4.2 Step 4b — Ads intelligence sweep (the new capability)

For every job (B2B and B2C), after the general Tavily search, run:

```bash
python3 <skill_dir>/scripts/reverse_run.py \
  facebook_ads search-ads "<2-3 niche keywords from the ICP>" --country MY
```

What you get per advertiser (real example, verified):
```
page: {name: "Klinik MyFamily Penang", page_id, url, like_count}
landing_domains: ["api.whatsapp.com"]        ← contact channel!
status: {is_active: true, delivery dates}    ← proof of ad spend
```

**How to use advertisers as leads:**
- `name` = page name, `website` = page URL, `source` = the `ads_library_url` or `source_url` from the result
- `notes` = "Active advertiser on Meta (ads since <start_date>)" — this is a **strong buying signal**: the business already spends on marketing
- `fit_score`: +1 over your base score for active advertisers (they have budget)
- **Landing domains go in the `website` field** — this directly fixes the weak website coverage (~15%) seen in past jobs
- If the landing domain is `api.whatsapp.com/<number>` → extract the number into `phone`
- Cap: take the top 10-15 most relevant advertisers per query; don't flood the list with off-niche pages

Optional second sweep for B2C jobs with visual products:
```bash
python3 <skill_dir>/scripts/reverse_run.py tiktok creative-top-ads --country MY   # if supported
python3 <skill_dir>/scripts/reverse_run.py microsoft_ads search-ads "<keywords>"
```

### 4.3 Step 4d — Free enrichment before paid

| Gap in a lead | Try first (free) | Fallback (paid/other) |
|---|---|---|
| No decision-maker at a known company | `reverse linkedin company-people <slug>` | Tavily `include_domains: [linkedin.com]` |
| No contact on a local SME | `reverse facebook_ads page-ads <page_id>` (their ads often list WhatsApp) | Tavily FB/IG domain search |
| Thin community context | `reverse reddit search "<org> <location>"` | web_search |

**LinkedIn expectation-setting**: anonymous LinkedIn calls frequently return HTTP 999 (anti-bot) from datacenter IPs. The wrapper classifies this as `blocked`. That is **normal and expected** — try once, then fall back. Don't burn time retrying.

### 4.4 Escalation passes — updated definitions

- **Vertical pass** (contactless leads) — now includes, before Tavily:
  1. `reverse facebook_ads page-ads <page_id>` — their running ads
  2. `reverse reddit search "<org name>"`
  3. `reverse youtube search "<org name>"` — channel often has contact info
  4. Then the existing Tavily social-domain searches
- **Horizontal pass** (ladder rungs L2→L4) — unchanged, but the ads sweep at the new rung's geography is now the cheapest first move (`--country MY` + regional keywords)

### 4.5 Error handling — the reverse rules

- `429` → stop the current reverse batch entirely, move on (platforms rate-limit aggressively)
- `blocked` (403/999) → one retry maximum, then fall back permanently for this job
- `session_required` / `not_installed` → skip the layer, note it in quality_gate if it materially hurt
- **Treat every reverse failure as "unavailable", NEVER as "no results"** — don't let a 429 make you believe a niche has no advertisers

### 4.6 Quality gate — reporting

Add one line to your `quality_gate` block:

```json
"reverse_used": true,
"reverse_leads_contributed": <N>
```

The 50-lead / 60%-contact target is unchanged. Ads intelligence typically adds 10-15 high-fit leads per job, which should make the target *easier* to hit without Phase 2.

---

## 5. Updated lead schema usage

No schema changes — reverse leads map onto the existing fields:

```
name            ← page.name / advertiser name
email           ← from landing page or org website (discover_email as before)
phone           ← from WhatsApp deep-link in landing_domains (strip api.whatsapp.com/)
address         ← from page or ads library region if present
website         ← page.url OR landing_domain (prefer the real site, not the WhatsApp link)
source          ← ads_library_url / source_url from the reverse result (REQUIRED — traceability)
profile         ← matched ICP as usual
fit_score       ← base score +1 for active advertisers
notes           ← "Active advertiser on <platform> (since <date>)" + normal notes
social_platform ← "facebook" (ad library pages)
social_handle   ← page alias/username if present
lead_type       ← "organization"
search_rung     ← the rung the ads query ran at (usually L1/L2)
```

**Dedup**: reverse ads pages may overlap with Tavily-found orgs — dedupe by normalized page URL / phone / name+address as you already do programmatically.

---

## 6. Quick reference — your platform whitelist

Use ONLY these from reverse (the other 16 are China-ecosystem platforms, irrelevant to BuzDev markets):

| Platform | Your most-used commands |
|---|---|
| `facebook_ads` | `search-ads "<kw>" --country MY`, `page-ads <page_id>`, `ad-details` |
| `linkedin` | `company <slug>`, `company-people <slug>`, `person <slug>` |
| `reddit` | `search "<query>"`, `subreddit <name>` |
| `youtube` | `search "<query>"`, `comments <video_id>` |
| `twitter` | `search-posts "<query>"`, `user <handle>` |
| `instagram` | `profile <handle>`, `posts <handle>` |
| `microsoft_ads` | `search-ads "<kw>"` |
| `pinterest_ads` | `search-ads "<kw>"` |
| `snapchat_ads` | `search-ads "<kw>"` |
| `tiktok` | `search-users "<kw>"`, `search-general "<kw>"`, `trending-searchwords` |

Discover exact parameters live: `reverse describe <platform> <command> --format json`

---

## 7. Verification checklist (after install)

Run these on the hosted agent to confirm the layer works end-to-end:

```bash
# 1. Ads search returns real data
python3 <skill_dir>/scripts/reverse_run.py facebook_ads search-ads "tahfiz" --country MY
# expect ok:true with items in the result file

# 2. Reddit works
python3 <skill_dir>/scripts/reverse_run.py reddit search "sekolah agama"
# expect ok:true, posts[] in file

# 3. LinkedIn fails gracefully (expected 999)
python3 <skill_dir>/scripts/reverse_run.py linkedin company microsoft
# expect {"ok": false, "error_kind": "blocked"} — this is CORRECT behavior

# 4. Executor reports not-installed correctly (simulate):
mv /opt/data/reverse/.venv /opt/data/reverse/.venv.bak
python3 <skill_dir>/scripts/reverse_run.py reddit search test
# expect {"ok": false, "error_kind": "not_installed"}
mv /opt/data/reverse/.venv.bak /opt/data/reverse/.venv
```

All four passing = the layer is production-ready. Then process your next queued job with the new Step 4 and report `reverse_used`/`reverse_leads_contributed` in the quality gate.

---

## 8. Maintenance

- **CLI updates**: `git -C /opt/data/reverse/src pull` + reinstall via `install.sh` (idempotent). Do this only when a platform breaks — the upstream repo is actively maintained but platforms change protocols without notice.
- **When a platform breaks** (persistent `failed` errors): note it in the skill's references, stop using that platform, rely on fallbacks. Don't try to fix reverse-engineered protocols yourself unless trivial.
- **Disk**: catalog + source + venv ≈ 200 MB under `/opt/data/reverse/`. Clean result files from `/tmp` per job (the executor leaves the last one for you to read; delete after ingestion).
- **This doc**: update `buzdev_user_request_workflow.md` §4/§5 to reference the reverse layer once installed, so the baseline doc stays the source of truth.

---

*Written by the local Hermes manager (root box) for the hosted Nous Portal agent. Questions/edge cases → Telegram.*